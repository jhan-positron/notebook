I am told TRON's router matrix calculation is a good use case for AMX. The motivation is to speed up prefill and decode perf for MoE
models such as gpt-oss. Please :
1. Ramp up: I am not familiar what MoE router is, how it is used in MoE; whether it is TRON framework or belonging to per model scope
   (if latter, is it hard code or generated from ingest?); is it only benefiting MoE, or dense models also
2. Build on top or update the on-going AMX project? At the moment, the AMX solutin does not support gpt-oss because their geometry
   does not fit the current implementation. It seems we have the following options:
   a: Add router/AMX to the current AMX implementation
   b: Add gpt-oss support first, and then add router/AMX on top
   Any other options? What do you recommend?

Generate HTML file for above.

The root of router/AMX is ./router, generate doc and artifacts under.

