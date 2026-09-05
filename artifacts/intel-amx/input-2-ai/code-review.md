# amx_attn_iface.hpp

## change "young"
`// the PAGE, not the query: a young query's COMPLETE pages take AMX`: "young" is not technical, please use other words or 
phrases. Do not be cute, use plain English.


# fill out xxx
`xxx` are my questions to you basically, please answer them in place of `xxx`.

Many of them are about variable and function naming. If they are explicitly defined or explained at Notes, you do not need
to follow my requests to replace them, but please add a comment to reference the Notes.

# remove referencing rampup doc
`p1` as in file name, p1_share_counters.hpp, refers to a step from project planning doc (right?). Such doc are not TRON
artifact, so we should remove all such references. 

Other references such as namespace tron::p1 are best to use different words.

# remove left-over during investigation
TRON_AMX_K_MIRROR_LAYOUT_ONLY is discarded already as a solution, there are still 3 places mentioning it, please clean up.

# memory leak test
mirror arena uses heap memory, do we have unit test to cover memory leak?

# use braces
```
          if (k_mirror_on)
                pg.template set_k_mirror<geometry.kv>(slot, kv_head, static_cast<size_t>(j),
                                        pg.template k<geometry.kv>(slot, kv_head, j).data);
```
I added braces at this code. The rule is, if all are on same line, no brace is fine; otherwise braces are needed.

Another example is the clause after `if (!did_amx)` should be braced.

Please scope the new code and apply this rule. Do not bother existing code.

# Clean up non tech words
`young query` in amx_attn_iface.hpp needs to change, replace "young" with plain English. Please search AMX code changes
and replace all such cute words.

# self_attention.hpp
` if constexpr (operation_kv_mul == 4 && operation_head_size == 128) {` : Is this check necessary? Its only clause is already guarded by did_amx.

I have questions, inlined(started with comment "xxx").

There are many places using scalars like 64, 16, 256, etc., please declare meaningful contant variables and use them. This helps reading code.

