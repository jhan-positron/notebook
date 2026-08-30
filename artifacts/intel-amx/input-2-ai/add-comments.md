# append comment to 1st arg of _tile_loadd
Here is function signature of _tile_loadd:
void _tile_loadd(constexpr int dst, const void *base, size_t stride)

Currently the calling code is something like:
 _tile_loadd(6, q_packed + step * TILE_ROWS * DIM_STEP, TILE_ROW_BYTES);

 Let's append a small comment after the first argument like this:

 _tile_loadd(6 /* dest tile */, q_packed + step * TILE_ROWS * DIM_STEP, TILE_ROW_BYTES);
 or
 _tile_loadd(6 // dest tile,
             q_packed + step * TILE_ROWS * DIM_STEP, TILE_ROW_BYTES);

Do this for all occurrances.

# add comments to _tile_dpbf16ps
Add small comments to each argument, e.g. from
 _tile_dpbf16ps(0, 4, 6);
to 
 _tile_dpbf16ps(0 /*dest tile*/, 4 /* src tile 0 */, 6 /* src tile 1 */ );

# add comments to _tile_stored
 Add small comments to arguments, e.g. from
_tile_stored(0, s_transposed + 0 * TILE_FP32S, TILE_ROW_BYTES);
to
_tile_stored(0 /* src tile */, s_transposed + 0 * TILE_FP32S, TILE_ROW_BYTES);

Do the above for all occurrances.
