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
- Keep other literals, including `1`, `true`, and `false`, in named declarations and refer to them by name. List any further exceptions explicitly.

```cpp
constexpr int DAYS_PER_WEEK_7 = 7;
constexpr int MAX_RETRIES_3 = 3;
bool ROW_ALIGNED_TRUE = true;
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
