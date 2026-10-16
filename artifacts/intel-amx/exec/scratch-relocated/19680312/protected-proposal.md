# Proposed edits to the four protected sections of the PR 4424 body (not applied)

Why: with PR 4737 merged, a run shorter than a block is no longer stored with masked
line stores, and a decode token is no longer scattered into 64 lines. Three passages of
the protected sections describe the old behaviour.

## Short version, paragraph 1 (two sentences replaced, one added)

Current:
> For passes of more than 16 tokens, the store uses a shared block save: runs of 2 to 16
> tokens are transposed in registers and written as 64-byte cache lines by the main thread
> and its idle helper threads. A single token, as in every decode step, does not form a
> block. Its 64 dimension pairs are written one by one into 64 cache lines.

Proposed:
> For passes of more than 16 tokens, the store uses a shared block save: a run that fills a
> whole 16-token block is transposed in registers and written as 64-byte cache lines by the
> main thread and its idle helper threads. A shorter run, and the single token of every
> decode step, is written row-major into the block's own 4 KiB: 4 whole cache lines per
> token. The block is converted to the VNNI layout in place at the end of the forward pass
> that saves its 16th row. Under FPGA attention the block stays row-major (the fix of
> issue #4500).

## "Remove the Score transpose by saving VNNI layout and transposed K", last sentence (one clause added)

Current:
> Partial pages, and every page when the AMX kernel does not run (...), go through a new
> AVX-512 reader.

Proposed:
> Partial pages, and every page when the AMX kernel does not run (...), go through a new
> AVX-512 reader. The tokens of a block that is still row-major are scored by the existing
> row-major dotter.

## "Use shared block in saving K", cases 2 and 3 of the block save (replaced)

Current:
> 2. 2 to 15 tokens (prefill edges): the same, but each line store is masked to the run's tokens.
> 3. 1 token (decode): no transpose. Each of the 4 steps loads 64 bytes of the row into one
>    register and scatters its 16 pairs into 16 cache lines, 4 bytes each: 4 scatters, 64 cache lines.

Proposed:
> 2. 2 to 15 tokens (prefill edges): row by row, 4 whole 64-byte lines per token, into the
>    block's row-major form (Note [Row-major tail block]). The block is converted to the VNNI
>    layout in place at the end of the forward pass that saves its 16th row.
> 3. 1 token (decode): the same row-major store, 4 whole lines, no scatter. The conversion
>    happens when the block completes, unless the operation's attention runs on the FPGA:
>    then the block stays row-major and the FPGA staging reads its rows in place (issue #4500).

The "Sharing" bullet of that section stays as it is.
