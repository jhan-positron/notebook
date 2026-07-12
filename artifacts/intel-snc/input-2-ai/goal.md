# configure sub NUMA, SNC/3 at Intel Xeon6 6962P system, delphi-3af6, run perf tests and 
  confirm the performance improves comparing disabled SNC. The comparisons include L3 
    latency, DRAM latency and DRAM throughput
      
## metrics:
    - L3 latency improved from 60ns to ~40ns
    - DRAM latency: exact metrics TBD
    - DRAM throughput: exact metrics TBD
## baseline
- The SNC-disabled baseline is MEASURED LIVE on this machine (the SNC-OFF pass of
  this same project, same tools), not taken from pre-work. The ~60 ns L3 / ~40 ns
  targets are expected anchors from pre-work + the SNC3 pass; the SNC-OFF pass
  produces this project's own pre-SNC3 numbers, and the success thresholds compare
  the two live same-machine passes.


## success / tolerance
    - L3 latency success threshold: SNC/3 must bring single-thread L3 hit
      latency to <= 45 ns (target ~40 ns; pre-SNC3 baseline ~60 ns).
    - Prediction agreement: a prediction "holds" if the measured value is
      within +-10% of predicted. Use percentage (not absolute ns) so the bar
      is consistent across the hierarchy (L1 ~1 ns to cross-socket DRAM ~300 ns).
      Below ~1 ns, the measurement noise floor (~0.1 ns) applies instead.
    - Action ladder when a prediction misses:
        +-10% to +-20% : explainable drift -> refine the model constant and note
                         it in "Analyze the gaps"; no perf needed.
        beyond +-20%   : structural -> explain it. If the cause is obvious
                         (e.g. DDR channel count), state it; otherwise run the
                         perf investigation in execute.md and conclude the gap.
    - Qualitative-surprise override: regardless of the % miss, a wrong ordering
      or sign, or an unexpected plateau/cliff (e.g. RMW latency LOWER than read),
      triggers the perf investigation. The % bands catch magnitude errors; this
      catches shape errors.

## math model
- The pre-work has some math models, e.g. calculating latencies after enabling SNC3. Compare the SNC3 test results with the prediction from the math model.
- Predict all SNC3-ENABLED test results from the SNC3-DISABLED (SNC-OFF) test data via the math model. Once test data exist for BOTH configurations (if a config has multiple datasets, use the latest), compare the predictions against the measured results.
- A prediction is not complete unless the derivation is recorded before
  measurement. Each predicted value/range must name its source data, row
  selectors, equation/topology rule, assumptions, tolerance, acceptance
  threshold if any, and falsification condition. Goals/targets are acceptance
  criteria, not evidence for the predicted value.
- Construct math models based on the test data from pre-work and SNC3:
-- data workset size
-- software code size
-- data access pattern
-- software architecture pattern (same/different software at different core/die/socket)
-- anything else you believe are needed. E.g. Intel's L1 and L2 are higher performant than AMD, how to factor this in the math model? And what measurement does the model need from measuring the target software?
-- basically define a model to help design future software at same Intel system. E.g. future software can predict performance at the system
-- sanity-check every directional claim (faster/slower, better/worse) against the
   raw per-configuration numbers before writing it; do not infer a trend from a
   mean that hides the spread.

# Able to answer the following questions: for an existing software, what should we measure and how should we measure in order to get what metrics so that we can predict its performance if we port the software to this Intel system:
1. SNC3 is not enabled
2. SNC3 is enabled

# If we cannot improve perf through SNC/3, we have definitive proof that SNC/3 is not 
      the solution and we propose new solution(s)
