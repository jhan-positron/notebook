#pragma once

#include <array>

#include "tron/models/kv_cache.hpp"

namespace tron::test {

// Allocation and copy tests identify a K row by its first element.
template <kv_geometry geometry, typename Page>
void set_k_tag(Page& page, kv_slot_id slot, size_t head, size_t token, bf16 tag) {
  alignas(64) std::array<bf16, geometry.head_size> row{};
  row[0] = tag;
  page.template set_k_row<geometry>(
      slot, head, token, k_source_row<geometry.head_size>(row.data()));
}

template <kv_geometry geometry, typename Page>
float k_tag(const Page& page, kv_slot_id slot, size_t head, size_t token) {
  alignas(64) std::array<bf16, geometry.head_size> row;
  page.template get_k_row<geometry>(
      slot, head, token, k_destination_row<geometry.head_size>(row.data()));
  return float(row[0]);
}

}  // namespace tron::test

