### Decode throughput (tok/s), this round vs the 2026-08-25 round at bbb55ae5f

| cell | canonical | ref | delta | mirror | ref | delta |
|---|---|---|---|---|---|---|
| qwen-3-4b-tp2 1u/2K | 211.2 | 212.7 | -0.7% | 214.6 | 213.3 | +0.6% |
| qwen-3-4b-tp2 1u/8K | 122.0 | 121.7 | +0.3% | 126.4 | 126.5 | -0.1% |
| qwen-3-4b-tp2 8u/2K | 52.3 | 52.3 | -0.0% | 55.7 | 55.4 | +0.5% |
| qwen-3-4b-tp2 8u/8K | 17.0 | 17.0 | -0.0% | 18.7 | 18.6 | +0.6% |
| llama-3.1-8b-tp2 1u/8K | 124.1 | 124.2 | -0.1% | 128.0 | 129.0 | -0.8% |
| llama-3.1-8b-tp2 8u/2K | 53.0 | 53.1 | -0.2% | 56.2 | 55.8 | +0.9% |
| mixtral-8x7b-tp2 8u/2K | 34.5 | 33.9 | +1.8% | 33.9 | 33.9 | +0.0% |
| mixtral-8x7b-tp2 8u/8K | 25.1 | 25.6 | -2.1% | 27.5 | 27.9 | -1.5% |

### gpt-oss-120b (AMX-ineligible), arms vs kill switch (TRON_AMX_DISABLE=1), same round

| cell | kill switch | canonical | delta | mirror | delta |
|---|---|---|---|---|---|
| gpt-oss-120b-tp2 1u/2K | 179.2 | 178.3 | -0.5% | 178.6 | -0.4% |
| gpt-oss-120b-tp2 1u/8K | 137.0 | 136.9 | -0.1% | 136.5 | -0.4% |
| gpt-oss-120b-tp2 8u/2K | 52.2 | 51.8 | -0.8% | 47.9 | -8.3% |
| gpt-oss-120b-tp2 8u/8K | 25.0 | 24.2 | -3.2% | 24.6 | -1.8% |
