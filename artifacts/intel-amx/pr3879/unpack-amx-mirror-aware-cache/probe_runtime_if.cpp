#include <concepts>
#include <cstddef>
#include <memory>
using std::size_t;

template <typename T>
concept sequence_cache = requires(size_t n, size_t s, bool e) {
  { T::try_create(n, s, e) } -> std::same_as<std::shared_ptr<T>>;
};

// jhan's proposal: run-time if on the flag instead of if constexpr on the type.
template <sequence_cache T>
std::shared_ptr<T> create_sequence_cache(size_t n_pages, size_t storage_slot_count,
                                         bool support_eagle, bool amx_mirror_eligible) noexcept {
  if (amx_mirror_eligible) {
    return T::try_create(n_pages, storage_slot_count, support_eagle, amx_mirror_eligible);
  } else {
    return T::try_create(n_pages, storage_slot_count, support_eagle);
  }
}

struct A_book {   // book-like: both overloads
  static std::shared_ptr<A_book> try_create(size_t, size_t, bool) noexcept;
  static std::shared_ptr<A_book> try_create(size_t, size_t, bool, bool) noexcept;
};
struct B_three_only {   // the "other conforming cache"
  static std::shared_ptr<B_three_only> try_create(size_t, size_t, bool) noexcept;
};
static_assert(sequence_cache<B_three_only>);

template std::shared_ptr<A_book> create_sequence_cache<A_book>(size_t, size_t, bool, bool);
#ifdef WITH_B
template std::shared_ptr<B_three_only> create_sequence_cache<B_three_only>(size_t, size_t, bool, bool);
#endif
int main() {}
