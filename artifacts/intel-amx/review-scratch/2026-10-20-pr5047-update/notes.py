import html
import re
import sys
from pathlib import Path

sys.path.insert(0, "/tmp/2026-10-20-pr5047-source")
from annotations import NEW as FIRST

EXACT = {}


def add(file, side, mapping):
    for number, text in mapping.items():
        EXACT[(file, side, number)] = text


add("h/tron/models/kv_cache.hpp", "new", {
28: "Includes the AMX scoring interface where the cache now invokes that kernel.",
29: "Includes the reusable query dot-product helpers in their new caller.",
31: "Includes the packed-key reader in its new caller.",
721: "Documents the new refusal point: the cache’s AMX operation rejects packed-key storage.",
722: "Documents the fallback to ordinary cache scoring after that refusal.",
723: "Preserves the restriction on packed-key AMX execution. This commit adds no packed AMX kernel.",
724: "Makes the cache responsible for choosing the packed reader or row-major dotters.",
725: "Retains the description of one packed token per CPU vector lane.",
726: "Retains the packed reader’s existing arithmetic organization.",
727: "States the new caller contract: provide queries and selected bits without inspecting storage layout.",
737: "Documents the replacement of public key-storage views with row transfers and scoring operations.",
738: "Keeps storage-layout decisions inside the cache for both layouts.",
1973: "Defines the scoring contract: write raw dot products only for selected offsets.",
1974: "Defines the query input and guarantees an empty selection does not access key storage.",
1975: "Makes attention geometry and the concrete query-view type template parameters.",
1976: "Accepts only a key/value geometry declared by this cache.",
1977: "Marks this small cache operation for inlining under the project’s attribute macro.",
1978: "Declares <code>score_k</code>, the new public operation for raw key scores. Its first argument selects the cache slot.",
1979: "Selects the key/value head whose stored keys will be read.",
1980: "Takes the complete query view by constant reference.",
1981: "Receives the 64-bit mask produced by attention’s existing token filters.",
1982: "Receives the address of the caller’s floating-point score array.",
1983: "Receives the distance between query-head output rows, in float elements. The method reads the cache and promises not to throw.",
1984: "Checks that every page offset fits in the selected-token mask.",
1985: "Returns before obtaining the storage block when no token is selected. The caller can now invoke this method unconditionally.",
1986: "Names the compile-time number of query heads sharing this key/value head.",
1987: "Names the compile-time number of elements in each head.",
1988: "Obtains the internal block for this geometry, slot, and key/value head after the empty-selection check.",
1989: "Chooses the packed-key branch at compile time.",
1990: "Invokes the same packed scoring kernel used by the first commit.",
1991: "Passes the internal packed view, the query-group start, selection mask, output pointer, and row stride.",
1992: "Begins the row-major alternative.",
1993: "Derives the dotter’s scalar type from the actual query-view type. Removes const/volatile qualifiers. The old attention-local code used the plugin tensor alias instead.",
1994: "Creates a templated lambda that expands compile-time query-head indices.",
1995: "Starts a fixed array initialized directly with query helpers.",
1996: "Constructs each dotter from its head’s query slice. The group-offset formula is retained.",
1997: "Calls the constructor lambda with the index sequence from zero through the final group head.",
1998: "Obtains the row-major key view internally. The view no longer crosses the page interface.",
1999: "Iterates selected bits in increasing offset order. Each update clears the lowest remaining bit.",
2000: "Finds the next selected page offset by counting low-order zero bits.",
2001: "Visits every query head sharing this key row.",
2002: "Writes the raw dot product to the caller’s strided output. This replaces the attention-local two-dimensional array indexing.",
2003: "Ends the query-head loop.",
2004: "Ends the selected-token loop.",
2005: "Ends the layout-specific reader choice.",
2008: "Compiles the AMX operation only when AMX dispatch support is enabled in the build.",
2009: "Defines the refusal contract: return false without changing scores or accessing storage.",
2010: "Explains that unsupported key layouts can refuse the operation. The query input is already packed.",
2011: "Requires a four-head bf16 query group and a caller that checked runtime AMX availability.",
2013: "Restricts the operation to a geometry declared by the cache.",
2014: "Marks the cache’s AMX wrapper for inlining.",
2015: "Declares a boolean attempt operation. The result says whether AMX scoring ran.",
2016: "Selects the key/value head to score.",
2017: "Receives the already packed bf16 query-group buffer.",
2018: "Receives the caller-owned output scores.",
2019: "Receives the output-head stride in float elements. The operation is read-only with respect to the cache.",
2020: "Requires 128 elements per key head at compile time. This does not broaden the caller’s existing head-count or scalar gate.",
2021: "Tests whether the key plane uses the packed layout.",
2022: "Declines packed keys. No score is written before this return.",
2023: "Begins the supported row-major AMX alternative.",
2024: "Calls the existing row-major AMX query–key kernel.",
2025: "Passes a row view obtained inside the cache and the caller’s existing query and score buffers.",
2026: "Reports successful AMX scoring.",
2027: "Ends the layout-based accept/refuse choice.",
2029: "Ends the build-time AMX-dispatch guard.",
2048: "Introduces a setter that accepts activation expressions and stores the cache’s bf16 representation.",
2049: "Parameterizes the setter by key geometry and expression implementation type.",
2050: "Requires that the cache declares this geometry.",
2051: "Marks the expression setter for inlining.",
2052: "Overloads <code>set_k_row</code> with a common expression-based entry point.",
2053: "Selects the key/value head being written.",
2054: "Selects the token offset within the page.",
2055: "Accepts one head-sized expression. The existing typed-bf16-row overload remains available.",
2056: "Checks that the token offset is within the page.",
2057: "Chooses packed storage at compile time.",
2058: "Allocates an aligned temporary bf16 row for the expression result.",
2059: "Evaluates and converts the expression into that temporary row.",
2060: "Delegates the packed write to the existing typed-row setter.",
2061: "Wraps the temporary buffer as a source row and passes the same slot, head, and offset.",
2062: "Begins the row-major alternative.",
2063: "Evaluates the expression directly into the cache’s row-major row.",
2064: "Ends the storage-layout choice.",
2065: "Ends the expression setter.",
2066: "Adds a blank separator before the existing row-loading operation.",
})

add("h/tron/models/model.hpp", "new", {
3100: "Calls the common cache setter for every storage layout.",
3101: "Passes the slot, head, token offset, and query-independent key expression <code>kout</code>. Conversion decisions move into the cache.",
})
add("h/tron/models/model.hpp", "old", {
3100: "Removes the model layer’s knowledge of the key-storage layout.",
3101: "Removes the local alias used to classify the key expression’s element type.",
3102: "Removes extraction of that type from the expression’s data pointer.",
3103: "Removes the model-local bf16 special case. The expression setter now owns conversion.",
3104: "Replaces the typed-row call inside the packed-only branch with the common setter call.",
3105: "Removes the direct source-row wrapper used for an already-bf16 packed input.",
3106: "Removes the separate non-bf16 conversion branch from the model.",
3107: "Moves responsibility for converting other activation types into the cache.",
3108: "Moves the temporary bf16 row out of the model’s save loop.",
3109: "Moves expression evaluation into the new setter’s packed branch.",
3110: "Moves the converted-row save into the cache’s setter implementation.",
3111: "Moves the temporary-buffer source view into the cache.",
3112: "Removes the closing brace of the model-local scalar-type choice.",
3113: "Removes the model-local row-major alternative.",
3114: "Removes the write through a public raw key row. The cache performs the equivalent row-major expression write internally.",
3115: "Removes the closing brace of the model-local layout choice.",
})

add("h/tron/models/self_attention.hpp", "new", {
1734: "Changes the dense-page operation to report success. A cache refusal can now fall back to software scoring.",
1748: "Documents delegation of raw dense-page scoring to the cache.",
1749: "Documents that a refused attempt leaves the attention accumulator untouched.",
1757: "Attempts raw AMX scoring through the cache interface.",
1758: "Passes the existing slot, head, packed query, score array, and score stride.",
1759: "Returns false immediately when the cache declines. Scaling and value accumulation have not started.",
1805: "Returns true after the dense-page attention update has completed.",
1869: "Retains the packed-query and dense-page prerequisites for attempting AMX.",
1870: "Documents the new cache refusal and software fallback.",
1871: "Preserves compile-time exclusion of unsupported head shapes and query types.",
1872: "Keeps the pointer to the existing dispatch design note.",
1874: "Retains the existing shape-and-scalar eligibility test. The layout test moves behind the cache interface.",
1877: "Adds another condition after the existing dense-page check.",
1878: "Attempts the dense-page operation only after the preceding conditions succeed.",
1879: "Enters the success return block only if that operation returns true. A false result falls through to software.",
1917: "Replaces the attention-local reader implementation with one cache scoring operation.",
1918: "Passes the same query view, selected mask, score array, and row stride. The cache handles an empty mask.",
})
add("h/tron/models/self_attention.hpp", "old", {
5: "Removes the bit-counting include from attention. The set-bit iterator now lives in the cache header, which already includes <code>&lt;bit&gt;</code>.",
25: "Moves the direct dotter dependency to the cache header.",
27: "Moves the direct packed-reader dependency to the cache header.",
1737: "Replaces the void return type with a success/failure result.",
1751: "Removes the description of a direct kernel call from attention.",
1752: "The scores remain unscaled, but the cache now owns the kernel call.",
1753: "The same output array remains. This old direct-reader description is replaced.",
1754: "Removes attention’s assumption that it can directly read the key storage.",
1755: "Removes the description of a public contiguous key-plane view.",
1756: "Moves this dependency on row-major storage into the cache.",
1757: "Replaces the layout-specific view description with the attempt-operation contract.",
1765: "Replaces the direct row-major AMX kernel call with the cache attempt.",
1766: "The same packed query and output arguments are passed through the new wrapper.",
1886: "Keeps the shape and query-type arguments while ending the eligibility expression here.",
1887: "Removes the layout exclusion from attention. The cache now declines unsupported layouts.",
1890: "Extends the condition to require that the dense-page operation succeeds.",
1891: "Moves the operation call into the condition so refusal can fall back.",
1892: "Retains these arguments in the boolean-returning call.",
})
for number in range(1875, 1885):
    EXACT[("h/tron/models/self_attention.hpp", "old", number)] = (
        "Replaces this part of the old dispatch comment. Shape and runtime prerequisites stay in attention. "
        "The cache now owns the key-layout acceptance decision."
    )
for number in range(1930, 1955):
    EXACT[("h/tron/models/self_attention.hpp", "old", number)] = (
        "Moves this part of software scoring into <code>page::score_k</code>. Its first-commit role was: "
        + FIRST[number]
    )
EXACT[("h/tron/models/self_attention.hpp", "old", 1938)] = (
    "Replaces the plugin-tensor scalar alias with the actual query-view element type inside the cache."
)

add("h/tron/scheduler/full.hpp", "new", {
2751: "Always requests a logical key row through the cache’s row-loading operation.",
2752: "Supplies the caller-owned destination buffer for this geometry, slot, head, and token.",
2753: "Returns that destination for both layouts. Row-major keys now incur a copy into scratch instead of returning the cache pointer.",
})
add("h/tron/scheduler/full.hpp", "old", {
2751: "Removes the scheduler’s compile-time key-layout choice.",
2752: "Removes the packed-only explanation of gathering into scratch.",
2753: "Removes the continuation of that packed-only comment.",
2754: "Keeps this logical row read but makes it unconditional across layouts.",
2755: "Keeps the caller-owned destination, now used for row-major keys too.",
2756: "Moves the destination return outside the old packed-only branch.",
2757: "Removes the row-major alternative.",
2758: "Removes the direct pointer to a row-major cache row. The replacement copies that row into the supplied destination.",
2759: "Ends the removed scheduler-level layout choice.",
})


def cache_old(text, number):
    s = text.strip()
    if 718 <= number <= 739:
        return "Replaces this description of public views and attention-local layout decisions with the new cache-operation contract."
    if s.startswith("//"):
        return "Removes the description of a public key-storage view. Callers now request row transfers or scores."
    if not s:
        return "Removes a blank separator between deleted view overloads."
    if s.startswith("TRON(nodiscard"):
        return "Removes result-use, inlining, and purity attributes attached to the deleted view accessor."
    if s == "TRON(this_lifetimebound)":
        return "Removes the lifetime annotation for a borrowed storage view that is no longer returned."
    if s.startswith("template "):
        return "Removes the template declaration for this geometry-specific public view overload."
    if "requires(" in s:
        return "Removes the availability constraint of the deleted view accessor. The replacement operations validate declared geometry internally."
    if "!k_vnni::layout_on" in s or s == "k_vnni::layout_on<geometry.head_size>)":
        return "Removes the layout restriction on a deleted storage-view accessor."
    if s.startswith("auto k("):
        scope = "one token’s row" if "i_page" in s else "the key plane"
        constness = "read-only" if " const " in s else "writable"
        return f"Removes this public {constness} view of {scope}. Storage layout no longer determines the caller’s interface."
    if s.startswith("return kv_block") and "as_view" in s:
        return "Removes direct exposure of the packed plane’s view. The packed scorer obtains it inside the cache."
    if s.startswith("return kv_block"):
        return "Removes direct exposure of the internal row-major key plane."
    if s.startswith("return k(") or s.startswith("return k<"):
        return "Removes token indexing through the public plane view. Row transfer operations replace this access."
    if s.startswith("k_vnni_view"):
        return "Removes the public packed-plane accessor <code>k_packed</code>."
    if s.startswith("kv_slot_id slot"):
        return "Removes the parameters and borrowed-lifetime declaration of the packed-plane accessor."
    if s == "{":
        return "Removes the opening brace of the deleted accessor body."
    if s == "}":
        return "Removes the closing brace of the deleted accessor body."
    return None


def note(record):
    f, side, number, text = record["file"], record["side"], record["line"], record["text"]
    key = (f, side, number)
    if key in EXACT:
        return EXACT[key]
    if f == "h/tron/models/kv_cache.hpp" and side == "old":
        return cache_old(text, number)
    if f == "h/tron/tensor/k_vnni.hpp":
        return ("Updates the documented page operation from exposing packed storage to scoring keys."
                if side == "new" else "Removes the deleted packed-view accessor from this list of supported page operations.")
    if f == "t/t_amx_dispatch_dtype.cpp":
        return ("Updates the test’s explanation: the cache now refuses packed-key AMX scoring. Test expectations are unchanged."
                if side == "new" else "Removes the explanation that attention itself compiles out the packed-layout path.")
    return test_note(record)


def test_note(record):
    s = record["text"].strip()
    side = record["side"]
    if s == '#include "kv_cache_helpers.hpp"':
        return "Includes the new test helpers for writing and reading row markers through the cache operations."
    if "test::set_k_tag<" in s:
        return "Writes the test’s identifying value through the row-transfer helper. The helper puts the marker in element zero and zeros the rest of the row."
    if "test::k_tag<" in s:
        return "Reads element zero through the row-transfer helper and checks the same expected marker. The surrounding allocation, retention, or copy assertion keeps its original purpose."
    if side == "old" and ("->template k<" in s or "page->k(" in s):
        return ("Removes the assertion’s direct read of cache element zero. The replacement reads that marker through the logical row interface."
                if "REQUIRE" in s else
                "Removes direct access to cache element zero. The replacement helper transfers a logical row without exposing its storage.")
    if side == "old" and ("[0]) ==" in s or "[0])" in s):
        return "Removes this continuation of the direct-element assertion. Its slot, head, token, and expected marker are preserved in the helper call."
    if side == "old" and ("bf16(" in s or "static_cast<bf16>" in s):
        return "Removes the old marker assignment’s continuation. The replacement helper receives the same marker value."
    if side == "new" and ("bf16(" in s or "static_cast<bf16>" in s):
        return "Passes the same page, slot, head, token, and marker value to the row-transfer helper."
    if s == "REQUIRE(":
        return "Begins the marker assertion, split across lines to fit the longer helper call."
    return None


add("t/kv_cache_helpers.hpp", "new", {
1: "Prevents duplicate inclusion of this test helper header.",
2: "Separates the include guard from includes.",
3: "Includes the fixed-size array used as a logical row buffer.",
4: "Separates standard-library and project includes.",
5: "Includes the cache types and row-transfer operations.",
6: "Separates includes from the helper namespace.",
7: "Places these utilities in the project’s test namespace.",
8: "Separates the namespace opening from the helper description.",
9: "Explains the marker convention: these tests identify a key row by element zero.",
10: "Makes the writer work with a declared key geometry and any compatible page type.",
11: "Declares the marker writer. Its arguments identify the page, slot, head, token, and marker.",
12: "Creates a zero-initialized, 64-byte-aligned bf16 row of the geometry’s head size.",
13: "Sets the first element to the identifying marker. Other elements remain zero.",
14: "Stores the full logical row through the geometry-specific cache setter.",
15: "Passes the row address in the typed source-row wrapper.",
16: "Ends the marker writer.",
17: "Separates the writer from the reader.",
18: "Makes the reader work with the same geometry and compatible page types.",
19: "Declares the marker reader on a const page. It returns a float for test comparisons.",
20: "Allocates an aligned destination row. The following get operation fills it.",
21: "Loads the logical row through the geometry-specific cache getter.",
22: "Passes the row address in the typed destination-row wrapper.",
23: "Returns element zero converted from bf16 to float.",
24: "Ends the marker reader.",
25: "Separates the last helper from the namespace close.",
26: "Ends the test namespace.",
})
add("t/t_llama_unit.cpp", "new", {
118: "Keeps the compile-time probe for accidental acceptance of an untyped slot index, now against the row-loading API.",
119: "Supplies a destination row and tries a raw size_t slot. Existing static assertions require this probe to be false.",
151: "Supplies the destination row required by the new geometry-access probe.",
152: "Checks whether the page supports logical row loading for this declared geometry and typed slot.",
153: "Ends the compile-time requires expression.",
457: "Requires logical row access for the supported geometry in every build. The preceding assertion rejects the removed packed-view accessor in every build.",
1047: "Changes the test visitor from a callback on a borrowed element to a write/read mode. No mutable storage reference escapes the cache.",
1054: "Computes the same identifying marker from slot, page, head, and whether this is the final token.",
1055: "Chooses the marker-writing phase of the test.",
1056: "Writes the marker with the common row helper.",
1057: "Passes the selected page, typed slot, head, token, and expected marker converted to bf16.",
1058: "Begins the verification phase.",
1059: "Begins the equality assertion for this row’s marker.",
1060: "Reads the marker through the cache getter and checks it against the same expected value.",
1061: "Ends the write/read mode choice.",
1068: "Seeds each slot using the visitor’s write mode.",
1070: "Verifies each seeded slot using the visitor’s read mode.",
1077: "Checks retained slots and the extra auxiliary slot after reclamation. The same selection condition remains.",
1082: "Seeds reclaimed slots after their storage is restored.",
1084: "Checks every slot after restoration.",
1087: "Renames the test to describe logical rows rather than borrowed storage views.",
1097: "Requires logical row access for every tested geometry, including packed geometries.",
1098: "Tests both allocated pages.",
1099: "Obtains the page containing the first token of this page index.",
1100: "Tests every key/value head declared by the geometry.",
1101: "Tests the first and last token offsets of each page.",
1102: "Creates aligned, zeroed source and destination row buffers.",
1103: "Seeds the first and last element positions of the source row.",
1104: "Begins assigning the identifying element value.",
1105: "Keeps the value formula based on slot, head, page, token, and element, then converts it to bf16.",
1107: "Writes the complete logical row through the geometry-specific cache setter.",
1108: "Wraps the source array as a typed row.",
1109: "Loads the same row through a const page and the explicit geometry.",
1110: "Supplies the token offset and typed destination row.",
1111: "Compares every element after the round trip. This checks the two seeded ends and the zero-valued interior.",
1112: "Also checks the convenience getter when the cache has one uniform geometry.",
1113: "Clears the destination before exercising that second getter.",
1114: "Loads the same row without spelling out the geometry template argument.",
1115: "Supplies the same destination buffer.",
1116: "Checks that the convenience overload returns the complete expected row.",
})
add("t/t_llama_unit.cpp", "old", {
117: "Replaces the old raw-index probe declaration with a requires expression that provides a destination row.",
118: "Removes the raw-index probe against the deleted public key-row view.",
150: "Replaces the geometry probe against the deleted view with a probe against logical row loading.",
453: "Removes the build-option split around the packed-view assertion.",
454: "Removes the expectation that a packed public view is available when packed keys are enabled.",
455: "Removes the start of the exact packed-view return-type assertion.",
456: "Removes the type check on the deleted packed-view accessor.",
457: "Removes the accessor arguments within that type check.",
458: "Removes the required public packed-view type; that representation is now private to cache operations.",
459: "Removes the alternative branch. Rejection of the public packed accessor now applies to all builds.",
461: "Removes the end of the former packed-view build-option split.",
1051: "Removes the callback that accepted a mutable reference to an internal key element.",
1058: "Removes borrowing element zero from the cache’s key row.",
1059: "Moves the marker formula out of the callback invocation. Row helpers now perform writes and checks.",
1066: "Replaces the marker-writing callback with the visitor’s write mode.",
1068: "Replaces the marker-checking callback with the visitor’s read mode.",
1075: "Retains this slot-selection condition while combining it with the read-mode call.",
1076: "Replaces the retained-slot verification callback with the read-mode call.",
1081: "Retains this reclaimable-slot condition while combining it with the write-mode call.",
1082: "Removes the multiline callback invocation.",
1083: "Replaces the callback assignment with the visitor’s write mode.",
1085: "Replaces the final verification callback with the visitor’s read mode.",
1088: "Removes the old test name referring to storage views.",
1098: "Removes the branch that excluded packed geometries from the row-addressing test.",
1099: "Removes the note delegating packed-row coverage entirely to another test.",
1100: "Removes the assertion that packed geometry lacks the tested access API.",
1101: "Removes that packed-access rejection. Logical row access is now supported for either layout.",
1102: "Removes the row-major-only alternative. The replacement round-trip test runs for both layouts.",
1103: "Retains the two-page loop outside the deleted layout choice.",
1104: "Retains page lookup in the common test body.",
1105: "Retains the all-heads loop in the common test body.",
1106: "Removes the writable public key-plane view.",
1107: "Removes the declaration of the const key-plane view.",
1108: "Removes obtaining the const key-plane view.",
1109: "Removes the compile-time check on a public view’s dimension type.",
1110: "Removes the expected two-dimensional storage-view shape.",
1111: "Removes the default-constructed lazy key view.",
1112: "Removes the check that the default borrowed view is invalid.",
1113: "Removes assignment of the const storage view into the lazy view.",
1114: "Removes the check that the borrowed view becomes valid after assignment.",
1115: "Moves uniform-geometry coverage to logical row loading.",
1116: "Removes the mutable-view pointer-identity assertion.",
1117: "Removes the const-view pointer-identity assertion. The row-transfer API returns values into caller storage.",
1119: "Retains first/last-token coverage in the common round-trip test.",
1120: "Removes the beginning of the plane-row versus token-row pointer-identity check.",
1121: "Removes the direct token-row pointer used by that identity check.",
1122: "Retains first/last-element seeding in the new row buffer.",
1123: "Replaces the single temporary element value with assignment into the source array.",
1124: "Retains this marker formula, with the loop variable renamed from row to token.",
1125: "Removes writing through the borrowed plane view.",
1126: "Replaces the per-element lazy-view check with equality of the full loaded row.",
1127: "Removes the old element-loop closing brace at this location.",
1227: "Removes the build-option split around geometry access.",
1228: "Removes the note about lack of a contiguous packed row. Logical row loading does not need contiguous storage.",
1229: "Removes the expected failure of access for packed 128-element heads.",
1230: "Removes the alternate branch. The retained positive access assertion now applies in every build.",
1232: "Removes the end of the geometry-access build-option split.",
1266: "Preserves the expected marker of 11 in the rewritten copy assertion.",
2024: "Preserves the expected marker derived from the source token plus one in the rewritten row-copy assertion.",
2073: "Preserves the primary-slot marker derived from the source token plus one.",
2077: "Preserves the auxiliary-slot marker derived from the source token plus eleven.",
})
add("t/t_llama_unit.cpp", "new", {
1886: "Keeps the expected marker of ten plus the token offset while reading through the row helper.",
1892: "Keeps the expected marker of thirty plus the token offset for the other retained slot.",
})
