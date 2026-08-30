// Probe for claims L2-L6 about the amx_mirror_aware_cache compound requirement.
// Compile: g++ -std=c++20 -fsyntax-only probe_amx_mirror_aware.cpp
#include <concepts>
#include <cstddef>
#include <memory>
#include <string>

using std::size_t;

// Minimal stand-in for sequence_cache: 3-arg static try_create returning shared_ptr<T>.
template <typename T>
concept sequence_cache = requires(size_t n_pages, size_t storage_slot_count, bool support_eagle) {
  { T::try_create(n_pages, storage_slot_count, support_eagle) } -> std::same_as<std::shared_ptr<T>>;
};

// The concept under discussion, verbatim from kv_cache.hpp.
template <typename T>
concept amx_mirror_aware_cache = sequence_cache<T> && requires(size_t n_pages,
                                                          size_t storage_slot_count,
                                                          bool support_eagle,
                                                          bool amx_mirror_eligible) {
  {
    T::try_create(n_pages, storage_slot_count, support_eagle, amx_mirror_eligible)
  } -> std::same_as<std::shared_ptr<T>>;
};

// Dispatcher shaped like create_sequence_cache.
template <sequence_cache T>
std::shared_ptr<T> create_sequence_cache(size_t n_pages, size_t storage_slot_count,
                                         bool support_eagle, bool amx_mirror_eligible) {
  if constexpr (amx_mirror_aware_cache<T>) {
    return T::try_create(n_pages, storage_slot_count, support_eagle, amx_mirror_eligible);
  } else {
    return T::try_create(n_pages, storage_slot_count, support_eagle);
  }
}

// (a) book-like: 3-arg (via defaulted 4th) and 4-arg noexcept, both returning shared_ptr<Self>.
struct A_book {
  static std::shared_ptr<A_book> try_create(size_t, size_t, bool);
  static std::shared_ptr<A_book> try_create(size_t, size_t, bool, bool) noexcept;
};

// (a2) book-like with a single 4-arg overload whose 4th param is defaulted (alternate "3-arg via default").
struct A2_book_defaulted {
  static std::shared_ptr<A2_book_defaulted> try_create(size_t, size_t, bool, bool = false) noexcept;
};

// (b) 3-arg only.
struct B_three_only {
  static std::shared_ptr<B_three_only> try_create(size_t, size_t, bool);
};

// (c) 4-arg whose 4th parameter is int (bool -> int is an integral promotion).
struct C_int4 {
  static std::shared_ptr<C_int4> try_create(size_t, size_t, bool);
  static std::shared_ptr<C_int4> try_create(size_t, size_t, bool, int);
};

// (d) 4-arg returning shared_ptr<Derived>, Derived : Self (convertible to shared_ptr<Self>, not same).
struct D_base;
struct D_derived;
struct D_base {
  static std::shared_ptr<D_base> try_create(size_t, size_t, bool);
  static std::shared_ptr<D_derived> try_create(size_t, size_t, bool, bool);
};
struct D_derived : D_base {};
// sanity: the return type IS convertible to shared_ptr<D_base>
static_assert(std::convertible_to<std::shared_ptr<D_derived>, std::shared_ptr<D_base>>);

// (e) 4-arg returning shared_ptr<Self>& (reference to a static).
struct E_ref {
  static std::shared_ptr<E_ref> try_create(size_t, size_t, bool);
  static std::shared_ptr<E_ref>& try_create(size_t, size_t, bool, bool);
};

// (f) 4-arg NOT noexcept.
struct F_not_noexcept {
  static std::shared_ptr<F_not_noexcept> try_create(size_t, size_t, bool);
  static std::shared_ptr<F_not_noexcept> try_create(size_t, size_t, bool, bool);  // no noexcept
};

// (g) 4-arg whose 4th parameter is std::string (bool does not convert to std::string).
struct G_string4 {
  static std::shared_ptr<G_string4> try_create(size_t, size_t, bool);
  static std::shared_ptr<G_string4> try_create(size_t, size_t, bool, std::string);
};

// (h) extra: 4-arg returning shared_ptr<Self> const (same_as strips nothing: prvalue of const class type
//     has type 'const shared_ptr<T>' -> not same_as shared_ptr<T>). Included to pin exactness further.
struct H_const_ret {
  static std::shared_ptr<H_const_ret> try_create(size_t, size_t, bool);
  static const std::shared_ptr<H_const_ret> try_create(size_t, size_t, bool, bool);
};

// (i) extra: what the looser alternative would accept — convertible_to version of the concept.
template <typename T>
concept amx_mirror_aware_cache_loose = sequence_cache<T> && requires(size_t a, size_t b, bool c, bool d) {
  { T::try_create(a, b, c, d) } -> std::convertible_to<std::shared_ptr<T>>;
};

// (j) extra: noexcept-checking form of the concept, to show the difference.
template <typename T>
concept amx_mirror_aware_cache_noexcept = sequence_cache<T> && requires(size_t a, size_t b, bool c, bool d) {
  { T::try_create(a, b, c, d) } noexcept -> std::same_as<std::shared_ptr<T>>;
};

// ---- all probe types satisfy the base concept ----
static_assert(sequence_cache<A_book>);
static_assert(sequence_cache<A2_book_defaulted>);
static_assert(sequence_cache<B_three_only>);
static_assert(sequence_cache<C_int4>);
static_assert(sequence_cache<D_base>);
static_assert(sequence_cache<E_ref>);
static_assert(sequence_cache<F_not_noexcept>);
static_assert(sequence_cache<G_string4>);
static_assert(sequence_cache<H_const_ret>);

// ---- expected truth values of amx_mirror_aware_cache ----
static_assert( amx_mirror_aware_cache<A_book>);            // (a) L6: 4-arg overload selected
static_assert( amx_mirror_aware_cache<A2_book_defaulted>); // (a2)
static_assert(!amx_mirror_aware_cache<B_three_only>);      // (b) L6: no viable overload -> false, not hard error
static_assert( amx_mirror_aware_cache<C_int4>);            // (c) L5: bool->int conversion accepted
static_assert(!amx_mirror_aware_cache<D_base>);            // (d) L3: shared_ptr<Derived> != shared_ptr<Self>
static_assert(!amx_mirror_aware_cache<E_ref>);             // (e) L3: shared_ptr<Self>& != shared_ptr<Self>
static_assert( amx_mirror_aware_cache<F_not_noexcept>);    // (f) L4: noexcept not checked
static_assert(!amx_mirror_aware_cache<G_string4>);         // (g) L5: bool does not convert to std::string
static_assert(!amx_mirror_aware_cache<H_const_ret>);       // (h) L3: const shared_ptr<Self> != shared_ptr<Self>

// ---- L3: the convertible_to alternative is looser ----
static_assert( amx_mirror_aware_cache_loose<D_base>);      // shared_ptr<Derived> converts
static_assert( amx_mirror_aware_cache_loose<E_ref>);       // shared_ptr<Self>& converts
static_assert( amx_mirror_aware_cache_loose<H_const_ret>); // const shared_ptr<Self> converts

// ---- L4: the noexcept form rejects the non-noexcept factory, accepts the noexcept one ----
static_assert( amx_mirror_aware_cache_noexcept<A_book>);
static_assert(!amx_mirror_aware_cache_noexcept<F_not_noexcept>);

// ---- L2: type of the expression is decltype((expr)) and is the FIRST template arg of same_as ----
static_assert(std::same_as<decltype((A_book::try_create(size_t{}, size_t{}, bool{}, bool{}))),
                           std::shared_ptr<A_book>>);
static_assert(std::same_as<decltype((E_ref::try_create(size_t{}, size_t{}, bool{}, bool{}))),
                           std::shared_ptr<E_ref>&>);
static_assert(std::same_as<decltype((D_base::try_create(size_t{}, size_t{}, bool{}, bool{}))),
                           std::shared_ptr<D_derived>>);

// ---- L6 / C8: the if-constexpr dispatcher instantiates for (b) and for (a) ----
template std::shared_ptr<B_three_only> create_sequence_cache<B_three_only>(size_t, size_t, bool, bool);
template std::shared_ptr<A_book>       create_sequence_cache<A_book>(size_t, size_t, bool, bool);
template std::shared_ptr<C_int4>       create_sequence_cache<C_int4>(size_t, size_t, bool, bool);
static_assert(std::same_as<decltype(create_sequence_cache<B_three_only>(1, 2, false, true)),
                           std::shared_ptr<B_three_only>>);

// ---- L1: requires-expression parameters are lvalues of their declared types (never evaluated) ----
template <typename T>
concept param_is_lvalue = requires(bool b, size_t n) {
  { b } -> std::same_as<bool&>;
  { n } -> std::same_as<size_t&>;
};
static_assert(param_is_lvalue<int>);

// ---- L7: amx_mirror_aware_cache subsumes sequence_cache -> constrained overload picks it, no ambiguity ----
template <sequence_cache T>          constexpr int which(T*) { return 3; }
template <amx_mirror_aware_cache T>  constexpr int which(T*) { return 4; }
static_assert(which(static_cast<A_book*>(nullptr)) == 4);        // more-constrained overload wins
static_assert(which(static_cast<B_three_only*>(nullptr)) == 3);  // only the base overload is viable

int main() {}
