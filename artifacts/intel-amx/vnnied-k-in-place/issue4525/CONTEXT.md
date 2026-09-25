# KV-cache tensor vocabulary

This glossary names the stored attention data discussed in issue #4525.

## Language

**KV cache**:
The saved key and value vectors for tokens that later attention operations can read.

**Native K**:
Key vectors stored as one contiguous dimension-ordered row per token.
_Avoid_: unqualified "native layout" when discussing values.

**Packed V**:
Value vectors stored with adjacent tokens interleaved for each dimension.
_Avoid_: "packed" alone when keys and values are both in scope.

**Blocked packed K**:
Key vectors stored as paired dimensions within token blocks for direct attention-kernel consumption.
_Avoid_: treating it as the same representation as packed V.

**KV slot**:
One persistent key/value region used by one layer or shared by several layers.

**Cache page**:
A group of token positions with key/value storage for each applicable slot and attention head.

**KV geometry**:
The number of key/value heads and the number of dimensions in each head.

**Live token**:
A token whose cache values are valid for the current reader.

**Padding token**:
An unused token position that a vector operation may still read.

**EAGLE storage**:
The cache region reserved for the speculative model's values.

