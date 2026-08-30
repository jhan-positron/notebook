// Extra-fact probe (supplement to probe_amx_mirror_aware.cpp). g++ -std=c++20 -fsyntax-only
#include <concepts>
#include <cstddef>
#include <memory>
using std::size_t;

template <typename T>
concept sequence_cache = requires(size_t n_pages, size_t storage_slot_count, bool support_eagle) {
  { T::try_create(n_pages, storage_slot_count, support_eagle) } -> std::same_as<std::shared_ptr<T>>;
};
template <typename T>
concept amx_mirror_aware_cache = sequence_cache<T> && requires(size_t n_pages, size_t storage_slot_count,
                                                          bool support_eagle, bool amx_mirror_eligible) {
  { T::try_create(n_pages, storage_slot_count, support_eagle, amx_mirror_eligible) } -> std::same_as<std::shared_ptr<T>>;
};
template <typename T>
concept loose = sequence_cache<T> && requires(size_t a, size_t b, bool c, bool d) {
  { T::try_create(a, b, c, d) } -> std::convertible_to<std::shared_ptr<T>>;
};

// X1: 4th parameter bool&& -- requires-expression parameter is an lvalue, cannot bind to rvalue ref.
struct X1 { static std::shared_ptr<X1> try_create(size_t, size_t, bool);
            static std::shared_ptr<X1> try_create(size_t, size_t, bool, bool&&); };
static_assert( sequence_cache<X1>);
static_assert(!amx_mirror_aware_cache<X1>);

// X2: 4th parameter bool& -- lvalue binds.
struct X2 { static std::shared_ptr<X2> try_create(size_t, size_t, bool);
            static std::shared_ptr<X2> try_create(size_t, size_t, bool, bool&); };
static_assert( amx_mirror_aware_cache<X2>);

// X3: 4-arg returns unique_ptr<Self>: same_as fails, convertible_to accepts (shared_ptr(unique_ptr&&) is implicit).
struct X3 { static std::shared_ptr<X3> try_create(size_t, size_t, bool);
            static std::unique_ptr<X3> try_create(size_t, size_t, bool, bool); };
static_assert(!amx_mirror_aware_cache<X3>);
static_assert( loose<X3>);

// X4: book-shaped, but the 4-arg overload ALSO defaults its 4th parameter -> 3-arg call ambiguous -> base concept false.
struct X4 { static std::shared_ptr<X4> try_create(size_t, size_t = 1, bool = false) noexcept;
            static std::shared_ptr<X4> try_create(size_t, size_t, bool, bool = false) noexcept; };
static_assert(!sequence_cache<X4>);
static_assert(!amx_mirror_aware_cache<X4>);   // fails on the leading conjunct

// X5: variadic template factory satisfies the shape.
struct X5 { template <class... A> static std::shared_ptr<X5> try_create(A...); };
static_assert( amx_mirror_aware_cache<X5>);

// X6: 4th parameter double (bool -> double is a floating-integral conversion).
struct X6 { static std::shared_ptr<X6> try_create(size_t, size_t, bool);
            static std::shared_ptr<X6> try_create(size_t, size_t, bool, double); };
static_assert( amx_mirror_aware_cache<X6>);

// X7: concept asked for a type that is not a sequence_cache at all: false, no error (short-circuit on first conjunct).
static_assert(!amx_mirror_aware_cache<int>);

// X8: the 3-arg call is a prvalue call expression; decltype((call)) == return type (no reference added).
static_assert(std::same_as<decltype((X2::try_create(size_t{}, size_t{}, bool{}))), std::shared_ptr<X2>>);
int main() {}
