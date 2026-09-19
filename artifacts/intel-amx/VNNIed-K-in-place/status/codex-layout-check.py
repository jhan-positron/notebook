#!/usr/bin/env python3
"""Check packed-key ordering with unique raw bits and algebra with exact integers.

This is a design validator, not a test of compiled code or machine timing.
"""

import json
from pathlib import Path
import struct


TOKENS = 64
DIMS = 128
PANEL_TOKENS = 16
QUERY_ROWS = 4


def key_index(token, dim):
    return (((token // 16) * (DIMS // 2) + dim // 2) * 16
            + token % 16) * 2 + dim % 2


def reference_key(token, dim):
    return ((token * 19 + dim * 7 + token * dim) % 15) - 7


def reference_query(row, dim):
    return ((row * 11 + dim * 3 + row * dim) % 7) - 3


def append_key(storage, token):
    for dim in range(DIMS):
        storage[key_index(token, dim)] = reference_key(token, dim)


def qk_via_tile_addresses(storage, active_rows):
    scores = [[0] * TOKENS for _ in range(QUERY_ROWS)]
    for panel in range(4):
        for step in range(4):
            # Each step consumes 16 packed rows of 32 values per row.
            tile_base = panel * 2048 + step * 512
            for row in range(QUERY_ROWS):
                for token_lane in range(16):
                    even = 0
                    odd = 0
                    for pair in range(16):
                        dim = step * 32 + pair * 2
                        q_even = reference_query(row, dim) if row < active_rows else 0
                        q_odd = reference_query(row, dim + 1) if row < active_rows else 0
                        offset = tile_base + pair * 32 + token_lane * 2
                        even += q_even * storage[offset]
                        odd += q_odd * storage[offset + 1]
                    scores[row][panel * 16 + token_lane] += even + odd
    return scores


def bf16_round(value):
    """Round the finite positive examples below to bfloat16, a 16-bit float."""
    bits = struct.unpack("<I", struct.pack("<f", value))[0]
    bits = ((bits + 0x7FFF + ((bits >> 16) & 1)) >> 16) << 16
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def main():
    indices = [key_index(token, dim)
               for token in range(TOKENS) for dim in range(DIMS)]
    assert sorted(indices) == list(range(TOKENS * DIMS))

    raw_keys = [[token * DIMS + dim + 1 for dim in range(DIMS)]
                for token in range(TOKENS)]
    raw_values = [value for row in raw_keys for value in row]
    assert len(set(raw_values)) == TOKENS * DIMS
    assert all(0 <= value <= 0xFFFF for value in raw_values)
    packed_bytes = bytearray(TOKENS * DIMS * 2)
    for token in range(TOKENS):
        for dim in range(DIMS):
            struct.pack_into("<H", packed_bytes, key_index(token, dim) * 2,
                             raw_keys[token][dim])

    # Build the required physical order without using the index formula.
    expected_words = []
    recovered_keys = [[None] * DIMS for _ in range(TOKENS)]
    cursor = 0
    for panel_start in range(0, TOKENS, PANEL_TOKENS):
        for pair_start in range(0, DIMS, 2):
            for token in range(panel_start, panel_start + PANEL_TOKENS):
                for component in range(2):
                    dim = pair_start + component
                    expected_words.append(raw_keys[token][dim])
                    recovered_keys[token][dim] = struct.unpack_from("<H", packed_bytes, cursor)[0]
                    cursor += 2
    expected_bytes = struct.pack(f"<{len(expected_words)}H", *expected_words)
    assert packed_bytes == expected_bytes, "Unique raw sentinels do not match the required physical order"
    assert recovered_keys == raw_keys, "Independent unpacking did not recover every raw sentinel"

    storage = [None] * (TOKENS * DIMS)
    preservation_checks = 0
    unwritten_checks = 0
    prior_positions = set()
    unwritten_positions = set()
    for token in range(TOKENS):
        append_key(storage, token)
        for previous in range(token):
            for dim in range(DIMS):
                assert storage[key_index(previous, dim)] == reference_key(previous, dim)
                preservation_checks += 1
                prior_positions.add((previous, dim))
        for unwritten in range(token + 1, TOKENS):
            for dim in range(DIMS):
                assert storage[key_index(unwritten, dim)] is None
                unwritten_checks += 1
                unwritten_positions.add((unwritten, dim))

    boundary_tokens = [0, 1, 15, 16, 17, 31, 32, 47, 48, 63]
    boundary_dims = [0, 1, 2, 31, 32, 63, 64, 95, 96, 126, 127]
    boundaries = [
        {"token": token, "dim": dim, "offset_bytes": key_index(token, dim) * 2}
        for token in boundary_tokens for dim in boundary_dims
    ]
    for item in boundaries:
        offset = item["offset_bytes"] // 2
        assert storage[offset] == reference_key(item["token"], item["dim"])

    valid_counts = [0, 1, 2, 15, 16, 17, 31, 32, 33, 47, 48, 49, 63, 64]
    score_checks = 0
    valid_score_checks = 0
    padded_token_score_checks = 0
    inactive_query_score_checks = 0
    qk_cases = 0
    max_score_error = 0
    for valid_tokens in valid_counts:
        page = [0] * (TOKENS * DIMS)
        for token in range(valid_tokens):
            append_key(page, token)
        for active_rows in range(1, QUERY_ROWS + 1):
            actual = qk_via_tile_addresses(page, active_rows)
            for row in range(QUERY_ROWS):
                for token in range(TOKENS):
                    expected = 0
                    if row >= active_rows:
                        inactive_query_score_checks += 1
                    elif token >= valid_tokens:
                        padded_token_score_checks += 1
                    else:
                        expected = sum(reference_query(row, dim) * reference_key(token, dim)
                                       for dim in range(DIMS))
                        valid_score_checks += 1
                    error = abs(actual[row][token] - expected)
                    max_score_error = max(max_score_error, error)
                    assert error == 0
                    score_checks += 1
            qk_cases += 1
    assert score_checks == (valid_score_checks + padded_token_score_checks
                            + inactive_query_score_checks)

    q_loads = []
    k_loads = []
    score_stores = []
    for step in range(4):
        for row in range(QUERY_ROWS):
            q_loads.extend(range(row * 256 + step * 64,
                                row * 256 + step * 64 + 64))
        for panel in range(4):
            for pair in range(16):
                base = panel * 4096 + step * 1024 + pair * 64
                k_loads.extend(range(base, base + 64))
    for panel in range(4):
        for row in range(QUERY_ROWS):
            base = row * 256 + panel * 64
            score_stores.extend(range(base, base + 64))
    assert sorted(q_loads) == list(range(QUERY_ROWS * DIMS * 2))
    assert sorted(k_loads) == list(range(TOKENS * DIMS * 2))
    assert sorted(score_stores) == list(range(QUERY_ROWS * TOKENS * 4))

    # Probability-times-value uses two passes of 64 output dimensions each.
    # Its reduction over 64 tokens requires two steps of 32 tokens each.
    probability_loads = []
    value_loads = []
    output_stores = []
    for dim_pass in range(2):
        for step in range(2):
            for row in range(QUERY_ROWS):
                base = row * 128 + step * 64
                probability_loads.extend(range(base, base + 64))
            for panel in range(4):
                for pair in range(16):
                    base = (step * 16 + pair) * 512 + dim_pass * 256 + panel * 64
                    value_loads.extend(range(base, base + 64))
        for panel in range(4):
            for row in range(QUERY_ROWS):
                base = row * 512 + dim_pass * 256 + panel * 64
                output_stores.extend(range(base, base + 64))
    assert sorted(set(probability_loads)) == list(range(QUERY_ROWS * TOKENS * 2))
    assert sorted(value_loads) == list(range(TOKENS * DIMS * 2))
    assert sorted(output_stores) == list(range(QUERY_ROWS * DIMS * 4))

    precision_cases = []
    for query_type, value in [("float32", 1 + 2 ** -12), ("float16", 1 + 2 ** -10)]:
        if query_type == "float16":
            value = struct.unpack("<e", struct.pack("<e", value))[0]
        reference_dot = value * 1.0
        rounded_dot = bf16_round(value) * 1.0
        assert reference_dot != rounded_dot
        precision_cases.append({"query_type": query_type,
                                "query_value": value,
                                "reference_score": reference_dot,
                                "score_if_query_is_rounded_to_bf16": rounded_dot,
                                "absolute_score_change": reference_dot - rounded_dot})

    results = {
        "status": "PASS",
        "scope": "Independent layout algebra and byte extents only. No compiled kernel or hardware was run.",
        "operand_domain": "Score algebra uses repeating small signed integers exactly representable in bf16 and float32, with exact sums. Layout ordering uses unique raw 16-bit sentinels without floating-point interpretation.",
        "page": {"tokens": TOKENS, "dimensions": DIMS, "elements": len(indices),
                 "bytes": len(indices) * 2, "panel_tokens": PANEL_TOKENS,
                 "panel_bytes": 4096, "unique_offsets": len(set(indices))},
        "layout_roundtrip": {"unique_raw_16_bit_sentinels": len(set(raw_values)),
                             "physical_order_word_checks": len(expected_words),
                             "recovered_coordinate_checks": sum(len(row) for row in recovered_keys),
                             "packed_bytes_checked": len(packed_bytes),
                             "expected_order": "Independent nested loops over panel, dimension pair, token, and pair component; does not use key_index.",
                             "sentinel_interpretation": "Raw unsigned 16-bit values only; no floating-point operations."},
        "append": {"writes_checked": TOKENS,
                   "prior_element_preservation_checks": preservation_checks,
                   "unwritten_element_preservation_checks": unwritten_checks,
                   "prior_distinct_coordinates_checked": len(prior_positions),
                   "unwritten_distinct_coordinates_checked": len(unwritten_positions),
                   "count_interpretation": "Preservation counts are repeated assertions across append steps, not distinct coordinates or distinct values. The small integer values repeat.",
                   "bytes_written_per_token": DIMS * 2,
                   "distinct_64_byte_rows_touched_per_token": DIMS // 2},
        "boundaries": boundaries,
        "qk": {"cases": qk_cases, "valid_token_counts": valid_counts,
               "active_query_rows": [1, 2, 3, 4], "score_checks": score_checks,
               "valid_active_score_checks": valid_score_checks,
               "active_query_padded_token_score_checks": padded_token_score_checks,
               "inactive_query_row_score_checks": inactive_query_score_checks,
               "count_interpretation": "The three score categories are disjoint. Total checks include padded token outputs and inactive query rows, with repeated logical scores across cases.",
               "maximum_absolute_score_error": max_score_error,
               "q_unique_read_bytes": len(set(q_loads)),
               "k_unique_read_bytes": len(set(k_loads)),
               "score_unique_write_bytes": len(set(score_stores)),
               "tile_dot_products_per_four_rows_full_page": 16,
               "q_tile_loads_per_four_rows_full_page": 4,
               "k_tile_loads_per_four_rows_full_page": 16,
               "score_tile_stores_per_four_rows_full_page": 4},
        "pv_extent": {"assumed_value_layout": "[32 token pairs][128 dimensions][2 bf16]",
                      "probability_row_stride_bytes": 128,
                      "value_row_stride_bytes": 512,
                      "output_row_stride_bytes": 512,
                      "probability_unique_read_bytes": len(set(probability_loads)),
                      "value_unique_read_bytes": len(set(value_loads)),
                      "output_unique_write_bytes": len(set(output_stores)),
                      "probability_minimum_padded_bytes": 512,
                      "output_minimum_padded_bytes": 2048,
                      "passes_over_output_dimensions": 2,
                      "steps_over_tokens_per_pass": 2,
                      "tile_dot_products_per_four_rows_full_page": 16},
        "precision_counterexamples": precision_cases,
        "limitations": [
            "No claim of bitwise equality for general floating-point inputs or alternate reduction orders.",
            "No check of NaN, infinity, denormal, or rounding behavior on AMX or AVX hardware.",
            "Tail keys and padded query rows are initialized to zero in this validator.",
            "Production code must mask invalid token scores before normalization.",
            "PV byte extents assume a conventional token-pair packed value layout, not a source-code audit.",
            "No throughput, latency, cache-traffic, or memory-bandwidth measurements."
        ],
        "primary_sources": [
            "https://cdrdv2-public.intel.com/782151/253667-sdm-vol-2b.pdf",
            "https://www.intel.com/content/www/us/en/developer/articles/code-sample/advanced-matrix-extensions-intrinsics-functions.html",
            "https://www.intel.com/content/www/us/en/developer/articles/technical/intel-deep-learning-boost-new-instruction-bfloat16.html"
        ]
    }
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"status": results["status"], "output": str(output),
                      "unique_raw_16_bit_sentinels": len(set(raw_values)),
                      "qk_cases": qk_cases, "score_checks": score_checks,
                      "valid_active_score_checks": valid_score_checks,
                      "active_query_padded_token_score_checks": padded_token_score_checks,
                      "inactive_query_row_score_checks": inactive_query_score_checks,
                      "prior_element_preservation_checks": preservation_checks,
                      "unwritten_element_preservation_checks": unwritten_checks,
                      "maximum_absolute_score_error": max_score_error}))


if __name__ == "__main__":
    main()
