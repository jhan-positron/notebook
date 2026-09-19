#include <cstddef>
#include <limits>
struct kv_geometry {
  size_t n_kv_heads;
  size_t head_size;

  constexpr bool operator==(kv_geometry const&) const noexcept = default;
};
struct attention_geometry {
  size_t n_query_heads;
  kv_geometry kv;

  constexpr size_t query_width() const noexcept {
    return n_query_heads * kv.head_size;
  }
  constexpr size_t kv_width() const noexcept {
    return kv.n_kv_heads * kv.head_size;
  }
  constexpr size_t kv_mul() const noexcept {
    return n_query_heads / kv.n_kv_heads;
  }
  constexpr bool valid() const noexcept {
    return n_query_heads > 0 && kv.n_kv_heads > 0 && kv.head_size > 0 &&
           n_query_heads % kv.n_kv_heads == 0 &&
           n_query_heads <= std::numeric_limits<size_t>::max() / kv.head_size &&
           kv.n_kv_heads <= std::numeric_limits<size_t>::max() / kv.head_size;
  }

  constexpr bool operator==(attention_geometry const&) const noexcept = default;
};
inline constexpr size_t MAX_KV_MUL_16 = 16;
int main() {
  constexpr attention_geometry geometry{32, {1, 128}};
  static_assert(geometry.valid());
  constexpr size_t kv_mul = geometry.kv_mul();
  static_assert(kv_mul == 32);
}
