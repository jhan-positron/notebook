---
name: cpp-coding-guide
description: Follow the C++ coding guide when writing, editing, or reviewing C++ code.
---

# C++ Coding Guide

Apply these rules to code you write or modify. When reviewing code, flag violations.

## Named values

- Define fixed values as named `constexpr` variables, except for the explicit literal exceptions below.
- Prefer literal `0` for zero initialization, resets, zero comparisons, and empty or disabled values when the surrounding code makes its meaning clear.
- Numeric literals are allowed in `alignas(...)`: the syntax already explains that the value specifies alignment in bytes. Prefer `alignas(64)` over introducing a constant that merely restates the alignment. Use a named constant when it expresses a shared requirement whose uses must change together.
- Use a named constant when the value encodes a domain-specific rule or the name explains meaning that is not apparent at the use site.
- Name `constexpr` variables using uppercase letters and underscores between words.
- Append the variable's value to its name, separated by an underscore.
- For values containing punctuation or spaces, use an uppercase representation valid in a C++ identifier.
- When editing a value in source code, rename the variable and update its uses so the suffix matches the new value.
- Keep other literals, including `1`, in named declarations and refer to them by name. List any further exceptions explicitly.
- Use a named `constexpr bool` only where a bool is passed as an argument in a function call or constructor call or template argument. The reason is, at call site a bare `true` or `false` does not say what it means.

```cpp
constexpr int DAYS_PER_WEEK_7 = 7;
constexpr int MAX_RETRIES_3 = 3;

// A named bool only at a call site: a bare
// literal does not say what it means.
constexpr bool ROW_ALIGNED_TRUE = true;
void pack(const rows_t& rows, bool row_aligned = true);
pack(rows, ROW_ALIGNED_TRUE);

// A literal bool in a return, an initialization, an assignment, or a
// comparison.
bool converted = false;
if (all_rows_saved) converted = true;
return converted;
```

## Braces

- Enclose control-flow bodies in braces, including bodies of `if`, `else`, `for`, `while`, and `do` statements.
- Braces may be omitted only when the entire statement, including its body and any `else` branches, appears on one physical line.
- Always retain braces where C++ syntax requires them.

```cpp
if (retryCount < MAX_RETRIES_3) {
    retry();
}

// Also allowed: the entire statement is on one line.
if (retryCount < MAX_RETRIES_3) retry();
```

## Hot paths

A hot path is code that runs once per token, once per page or once per layer. These rules apply there. Elsewhere, prefer the simplest code.

- Declare a scratch buffer without a fill when the next writer sets every element. A default constructor can zero-fill the buffer, and the declaration line does not show that work. Use the constructor that skips initialization, and add one comment line that names the writer. Keep the default constructor when any element is read before it is written.
- Pass a view when the reader accepts one. Do not copy into a temporary only to change the type. A view is an object that points at memory it does not own, such as `tron::const_view` or `std::span`. Before using a view, check that the source stays alive and unchanged while it is read, that the source and the destination do not overlap, and that the address meets the alignment the view type claims.
- Test the condition first. Prepare the inputs of a branch inside that branch, so that the other branch does not pay for them. Keep another order only with a measured reason, and state that reason in a comment.

```cpp
// The default constructor zero-fills the buffer. score_page then writes
// every element, so the fill is wasted work.
tensor<HEADS_16, PAGE_TOKENS_64> scores;
score_page(keys, query, &scores[0][0]);

// uninitialized: score_page writes every element before any read.
tensor<HEADS_16, PAGE_TOKENS_64> scores{uninitialized};
score_page(keys, query, &scores[0][0]);

// A copy made only to pass the row as an expression.
tensor<HEAD_SIZE_128> scratch;
std::memcpy(&scratch[0], row_begin, HEAD_SIZE_128 * sizeof(float));
v_star.set(fma(v_star, corr, scratch));

// A view over the same row. No bytes are copied.
constexpr bool ROW_ALIGNED_TRUE = true;
constexpr bool ROW_DMA_FALSE = false;
tron::const_view<float, ROW_ALIGNED_TRUE, ROW_DMA_FALSE, tron::seq<HEAD_SIZE_128>> row{
    row_begin};
v_star.set(fma(v_star, corr, row));

// The pack runs for every page, and a partial page never reads it.
const bf16* packed = pack_query(query, slot);
if (is_dense_page(page)) apply_dense_page(page, packed);

// The pack runs only for a page that reads it.
if (is_dense_page(page)) apply_dense_page(page, pack_query(query, slot));
```
