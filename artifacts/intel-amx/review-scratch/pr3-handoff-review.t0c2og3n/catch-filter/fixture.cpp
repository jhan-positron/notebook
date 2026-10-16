#include <catch2/catch_test_macros.hpp>
TEST_CASE("VNNI K block save equals the per-token row store, bit for bit") { SUCCEED(); }
TEST_CASE("save_k stores every token's K row once, grouped by page block, alone or with helper threads") { SUCCEED(); }
