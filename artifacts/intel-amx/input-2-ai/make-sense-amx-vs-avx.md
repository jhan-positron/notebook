Let's brainstorm a plan: how to make sense AMX boosted TRON decode performance?

My thoughts are:
- AMX is used on attention only, out of the whole fwd passes. So we can measure the run time of attention of AMX vs AVX-based.
- Let's say x ns is saved between AMX attention and AVX attention, then x * 36 is the total time saved out of one token genenration.
- At another project, we defined Fence 1 and Fence 3 are 2 Definitive Sync points. We can measure the run time of Fence 1 to 
  Fence 1, or Fence 3 to Fence 3, as one complete token generation time.  
- With the above data, we can calculate how much time AMX improved over AVX per token gen, and the percentage.

The above are straightforward, and we may already have the data and do not need to test again. Yet I still have some questoins:
1. The AMX boost, as calculated from above, is constant in theory per token gen. But why did larger contexts show better boost?
2. How about the number of instructions executed during attention between new solution vs the old? And how about cache miss, TLB
   misses, memory allocation/de-allocation? 
   - The key question is, we know AMX has 8x MAC throughput over AVX, what are other factors which could help or detriment the
     pure AMX/AVX boost ?


Please use PAL to validate your points with GPT-sol-5.6.

Please generate PR3879/make-sense-amx-vs-avx.html.
