#!/usr/bin/env python3
"""Scalar model of PR4557 copy_token observability, not a C++ test run.

Pinned source: 96a6220ab664f73f215c57d6ed7802bbacd4d7a2.
Models one bf16 dimension per token and the exact two-half word stores.
The deliberate mutation preserves the existing destination odd half in
exactly one even-destination branch, selected by source parity.
"""
import json

PAGE_TOKENS = 64
POISON = 0x7FC0


def pattern(token):
    return 0x3C00 + token * 64


def set_row(words, token, bits):
    pair = token // 2
    if token % 2 == 0:
        words[pair] = bits  # append_v_row: even write clears high half
    else:
        words[pair] = (words[pair] & 0xFFFF) | (bits << 16)


def get_row(words, token):
    return (words[token // 2] >> (16 * (token % 2))) & 0xFFFF


def copy_token(dst, dst_token, src, src_token, preserve_odd_for_src_parity):
    src_pair = src[src_token // 2]
    dst_pair = dst[dst_token // 2]
    if src_token % 2 == 0:
        if dst_token % 2 == 0:
            result = src_pair & 0xFFFF  # source lines 359-365
        else:
            result = (src_pair << 16) & 0xFFFF0000 | dst_pair & 0xFFFF
    else:
        if dst_token % 2 == 0:
            result = src_pair >> 16  # source lines 378-384
        else:
            result = src_pair & 0xFFFF0000 | dst_pair & 0xFFFF
    if dst_token % 2 == 0 and src_token % 2 == preserve_odd_for_src_parity:
        result = result | (dst_pair & 0xFFFF0000)
    dst[dst_token // 2] = result


def run_case(dst_tokens, total_tokens, poison_padding, mutation):
    dst = [0] * (PAGE_TOKENS // 2)
    src = [0] * (PAGE_TOKENS // 2)
    for token in range(dst_tokens):
        set_row(dst, token, pattern(token))
    if poison_padding:
        set_row(dst, total_tokens, POISON)
    source_bits = []
    for token in range(total_tokens - dst_tokens):
        bits = 0x7F80 if not poison_padding and token in (2, 3) else pattern(token)
        source_bits.append(bits)
        set_row(src, token, bits)
    for token in range(len(source_bits)):
        copy_token(dst, dst_tokens + token, src, token, mutation)
    expected = [pattern(token) for token in range(dst_tokens)] + source_bits
    row_bits_match = all(get_row(dst, token) == bits for token, bits in enumerate(expected))
    result = {
        "dst_tokens": dst_tokens,
        "total_tokens": total_tokens,
        "final_copy": {"source_token": len(source_bits) - 1, "destination_token": total_tokens - 1},
        "live_row_bits_match": row_bits_match,
    }
    if poison_padding:
        partner = get_row(dst, total_tokens)
        nan = (partner & 0x7F80) == 0x7F80 and (partner & 0x7F) != 0
        result.update({"padding_bits": f"0x{partner:04x}", "padding_is_nan": nan})
    return result


results = []
for name, mutation in [("correct", None), ("preserve_odd_for_even_source", 0), ("preserve_odd_for_odd_source", 1)]:
    results.append({
        "variant": name,
        "full_page_bit_checks": [run_case(start, 64, False, mutation) for start in (2, 3)],
        "odd_length_poison_checks": [run_case(start, 7, True, mutation) for start in (2, 3)],
    })
print(json.dumps({
    "scope": "Deterministic scalar copy model; no production C++ test or hardware execution",
    "revision": "96a6220ab664f73f215c57d6ed7802bbacd4d7a2",
    "cases": results,
}, indent=2))
