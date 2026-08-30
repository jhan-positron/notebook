# Sol deviation review (G0, router P0) - 2026-08-23

Model: gpt-5.6-sol via PAL bridge; requested by session 7ff0b556.
Full verdict below, verbatim.

**VERDICT: ENDORSE-DEVIATION**

The deviation is legitimate as a correction of a failed operationalization, not a license to replace the pre-registered result. The pre-registered computation remains **STOP** and must remain visible. The corrected computation may be used as the decision-relevant advisory result because it is the smallest code-consistent correction to the pre-recorded intent, is applied symmetrically, and survives the reported conservative treatment for 20b.

This endorsement does **not** validate every detail of the post-hoc residual model, nor does it make 120b a broadly positive production case.

1. **The evidence supports “operationalization error,” not gate-shopping, subject to explicit criteria in the decision record.**

   The pre-registration’s semantic intent was:

   > “The stall is the serial cost actually paid”

   at G0-preregistration.md lines 47–50, excerpt: `"The stall is the serial cost actually paid, so the net-gain computation uses it."`

   `context_start_text`: `Rationale: the round trip T3 − T2 can overlap`  
   `context_end_text`: `A(s) = Σ_ℓ stall(ℓ,s).`

   But the selected marker was specifically:

   > `"start_reading <logits channel>"`

   at lines 42–50, excerpt: `"(a-stall), THE G0 VARIABLE: ... 'start_reading <logits channel>'"`

   The generated execution mechanics falsify the assumption that this statement is where worker 0 pays the router dependency. The observed closure is unusually strong evidence: the top-k-output block ends at approximately helper entry plus helper logits wait plus top-k execution, while FPGA logits arrive at the same boundary. See p0-trace.html lines 159–161, excerpt: `"block ends +21.9 ≈ helper entry 10.6 + first-wait 10.9 + top-k 0.4 = 21.9"`.

   `context_start_text`: `Lanes are concurrent; solid = work`  
   `context_end_text`: `At 8u the block grows to 32.4 µs/layer.`

   The correction also moves only one statement, rather than selecting an arbitrary larger interval. That is qualitatively different from inspecting many possible spans and choosing the one that passes.

   Jhan should apply these criteria:

   - **Intent precedence:** Was the pre-data semantic estimand unambiguous independently of the marker? Here, “serial cost actually paid” was.
   - **Causal/code correspondence:** Does the replacement marker represent the same dependency in the generated program? Here, the top-k output cannot arrive without router logits.
   - **Minimality:** Is this the nearest boundary that fixes the mistake, rather than a favorable composite window? The one-statement movement satisfies this; additions beyond that boundary need separate scrutiny.
   - **Outcome independence:** Would the same correction have been made if it remained negative? The closure and code mechanics should be documented as the basis, not the positive result.
   - **Symmetry:** Was one formula applied to all models/configurations? It was.
   - **Auditability:** Are registered and corrected results both retained? They are, at p0-trace.html lines 67–80 and 443–448.
   - **Robustness to discretionary assumptions:** Does the decision survive a less favorable residual treatment? 20b does; that materially weakens a gate-shopping concern.
   - **No retroactive claim:** The corrected result must remain labeled deviation rather than being described as the original pre-registered result.

   **Recommended decision-record wording:**

   > “Jhan endorses the corrected boundary as a post-capture operationalization correction. The pre-registration unambiguously targeted the driving thread’s router-dependent serial cost but attached that intent to a logits-channel read that is nonblocking in the generated execution. Code mechanics and trace closure independently locate the dependency one statement later at the top-k-output read. The original pre-registered computation remains the formal registered result (STOP); the corrected computation is accepted as the decision-relevant deviation and must remain labeled as such. This endorsement is based on causal correspondence and minimality, not on the corrected outcome.”

2. **The top-k-output block is the right primary decision variable, but `A_corr` is slightly broader than the unquestionably recoverable quantity.**

   The plan correctly rejected gross round-trip latency as the gate variable because overlapped device latency is not necessarily recoverable. See G0-preregistration.md lines 45–52, excerpt: `"The stall is the serial cost actually paid"` and `"a-roundtrip ... never as the gate variable"`.

   The corrected top-k-output wait is therefore the proper observable critical-path quantity: it measures when worker 0 cannot advance because the router-dependent output has not arrived.

   However, `A_corr` is defined at lines 101–105 as:

   > `A_corr(s) = Σ_ℓ [stall_linear + stall_topk_read + wait_indices](ℓ,s)`

   `context_start_text`: `Both results are reported`  
   `context_end_text`: `helper kernel-entry latency (labeled est)`

   The approximately 19–33 µs `stall_topk_read` is well justified. The two small surrounding terms deserve conservative handling:

   - The approximately 0.3 µs logits read may be channel/latch contract overhead that remains if P1a continues to publish logits through the existing contract.
   - The approximately 0.2 µs `wait_indices` may similarly be an irreducible channel-operation or wakeup floor rather than router latency.
   - P1a explicitly preserves the existing channel/latch contract at 02-option-c-plan.md lines 160–165, excerpt: `"publishes logits with the existing channel/latch contract"`.

   `context_start_text`: `Execution semantics open`  
   `context_end_text`: `transfers unchanged to generated gpt-oss`

   These terms are too small to alter the 20b decision, but the defensible presentation is to make `stall_topk_read` the primary corrected estimand and treat the adjacent waits as recoverable only if P1a demonstrates their disappearance.

   **Recommended wording:**

   > “The accepted corrected estimand is the driving thread’s router-dependent top-k-output block. The adjacent logits-read and wait-indices slices are included in the reported `A_corr` arithmetic but are not presumed fully removable until the P1a trace demonstrates that they disappear or shorten. A sensitivity excluding those slices shall be retained.”

3. **Helper-entry latency can be hidden by a CPU router, but it is not intrinsically removed.**

   The report states at p0-trace.html lines 409–412:

   > “helpers still enter at ≈E = 10.6, top-k done ≈11; residual block ≈ max(0, E+SP − (t_cpu+2))”

   `context_start_text`: `CPU-world per layer`  
   `context_end_text`: `matches the bootstrap mean`

   Including helper-entry latency inside the observed baseline block is not itself double-counting. If CPU logits complete before the helpers enter, helper-entry delay remains in the system but may overlap CPU computation; only its unhidden tail remains on the critical path. Thus some of the observed `A_corr` can legitimately be recovered through overlap without eliminating the underlying scheduler latency.

   The caveat is that `E` is measured in the FPGA baseline. P1a can change it through:

   - worker-0 occupancy;
   - AMX/AVX frequency effects;
   - helper scheduling and synchronization;
   - cache and memory-bandwidth contention;
   - multi-worker orchestration.

   The plan already identifies this risk at 02-option-c-plan.md lines 167–173, excerpt: `"Reject a kernel configuration that wins standalone but increases segment (b), starves expert launches ... or interferes with other in-flight batches"`.

   `context_start_text`: `CPU scheduling and FPGA-feed check`  
   `context_end_text`: `erase the net gain`

   Therefore `E` is acceptable for a P0 prediction only as an explicitly conditional estimate. It cannot substitute for an integrated P1a measurement.

4. **The stated residual formula is a useful approximation for 20b, but it is not a complete general timing equation.**

   A more complete per-layer dependency model is conceptually:

   - helper starts top-k at the later of helper entry and CPU-logits publication;
   - helper then incurs top-k execution plus output publication/wakeup;
   - worker 0 blocks only for the portion after it reaches the top-k-output read.

   Consequently, the residual depends on something of the form:

   > completion = `max(E, cpu_logits_published) + SP + output_publish/wakeup`

   and residual is completion minus the time worker 0 reaches the output read, floored at zero.

   The current `max(0, E+SP-(t_cpu+2))` is accurate only under additional assumptions about the publication path and the timing represented by the 2 µs term. In particular, when `t_cpu > E`, helpers wait for CPU logits and top-k still must execute afterward. The present expression can return zero even though a small top-k/output wakeup residual necessarily remains.

   This does not appear decision-material:

   - `SP` is about 0.4 µs/layer in the shown 20b trace.
   - The 20b conservative corrected results remain +2.24% to +4.41%.
   - For 120b, adding a small late-logits top-k residual would not rescue the negative 1u cells and would only weaken the marginal positive cells.

   But the report should not call the current alternate calculation “maximally conservative.” At p0-trace.html lines 244–247, excerpt: `"the conservative variant removes the 2 µs channel-op allowance"` and `"120b's E, SP make R = 0 there"`.

   `context_start_text`: `g = (A − C − R)/T_step`  
   `context_end_text`: `120b 1u/2K rests on 6 steps`

   Removing an allowance does not account for top-k execution after late CPU-logits publication. “Reduced-overlap variant” would be more accurate.

   **Recommended decision-record wording:**

   > “The P0 residual model is accepted as an estimate, not as an exact counterfactual. Its `E+SP-(t_cpu+2)` form assumes the measured channel interval covers publication/read progression and does not fully express the late-logits branch where top-k executes after CPU completion. The decision therefore relies on the 20b margin under adverse sensitivity, while P1a must directly measure the residual. The existing alternate row shall be called a reduced-overlap sensitivity, not ‘maximally conservative.’”

5. **The 2 µs allowance is plausible but not yet independently defensible as a fixed counterfactual constant.**

   The timeline shows approximately 1.4 µs launch work and approximately 1.1 µs of channel operations before the long block at p0-trace.html lines 119–137. That supports the order of magnitude, but it does not establish that exactly 2 µs occurs after CPU computation in the host-router path.

   Because a larger allowance reduces `R` and improves the predicted gain, it should be sourced from measured named spans and defined before applying the model—not selected as an intuitively reasonable constant. The fact that 20b passes when the allowance is removed substantially mitigates this issue.

   Jhan should accept the main conclusion without endorsing 2 µs as a reusable model parameter. P1a should directly mark:

   - end of CPU logits computation;
   - logits publication;
   - helper top-k entry/start/end;
   - worker-0 top-k-output read entry/return.

6. **20b G0 verdict: PROCEED, with P1a-spike-first sequencing.**

   All four corrected 20b cells clear 1%, including the reported adverse sensitivity:

   - 1u/2K: corrected +5.36%, sensitivity +4.33% to +4.41%;
   - 1u/8K: +4.72%, sensitivity +3.82% to +3.88%;
   - 8u/2K: +3.58%, sensitivity +3.14% to +3.19%;
   - 8u/8K: +2.55%, sensitivity +2.24% to +2.27%.

   See p0-trace.html lines 232–243, especially lines 235–238.

   `context_start_text`: `<tr><th class="l">config</th>`  
   `context_end_text`: `20b 8u/8K`

   The margin is too large to be explained by the approximately 0.5 µs/layer questionable adjacent waits or the approximately 0.4 µs top-k-tail omission. This is enough to avoid the pre-registered STOP condition.

   This should authorize the already-planned mixed-host/device compile-and-run spike and a minimal P1a host-router A/B—not immediate P1b or broader AMX plumbing work. The plan itself requires that spike at 02-option-c-plan.md lines 143–152.

   **Recommended wording:**

   > “For gpt-oss-20b, G0 is PROCEED under the endorsed deviation. All four target decode configurations clear the 1% threshold with substantial margin, including the reduced-overlap sensitivity. Proceed in P1a-spike-first order. This is authorization to validate host placement, execution semantics, and integrated critical-path recovery; it is not an AMX shipping decision.”

7. **120b G0 verdict: mechanically non-STOP, but only conditionally PROCEED for validation—not a model-wide positive finding.**

   The measured single-core corrected results at p0-trace.html lines 239–242 are:

   - 1u/2K: −1.42%, based on only six retained steps;
   - 1u/8K: −2.67%;
   - 8u/2K: +1.35% [1.33, 1.37];
   - 8u/8K: +0.81% [0.79, 0.83].

   Under the literal pre-registered rule—STOP only if the upper 95% bound is below 1% in **all** target configurations—the measured 8u/2K cell prevents a formal STOP. See G0-preregistration.md lines 78–90, excerpt: `"STOP if the upper 95% bound of mean g is < 1% in ALL four target configs."`

   `context_start_text`: `Decision rules (pre-registered)`  
   `context_end_text`: `integrated measurement`

   Nevertheless:

   - two 1u configurations are clearly negative;
   - 8u/8K does not clear 1%;
   - the 8u/2K margin is small enough that integrated contention could erase it;
   - robust multi-configuration viability relies on the 4-worker AMX result, which is only an integrated-performance estimate;
   - the 4-worker design directly increases the scheduling/contention risk already carried by the plan.

   The measured 4-worker microbenchmark at p0-trace.html lines 362–365—`"4 workers over N at n=128 cyclic: amx 8.49 µs"`—is valid kernel evidence, but its claimed end-to-end benefit remains estimated.

   `context_start_text`: `Multi-core split point`  
   `context_end_text`: `Barrier and orchestration overhead is inside these numbers`

   Therefore 120b should not be recorded simply as “G0 PASS.” A precise result is **non-STOP / scoped validation warranted**, with no authorization to treat four-worker AMX as the selected production design.

   **Recommended wording:**

   > “For gpt-oss-120b, the literal G0 STOP condition is not met because the measured single-core 8u/2K projection clears 1%. The evidence is mixed rather than a model-wide pass: both 1u cells are negative and 8u/8K remains below threshold. Four-worker AMX viability is an integrated-performance estimate and is not used to pass G0. Retain 120b as conditional scope for a host-placement and scheduling spike after or alongside the 20b P1a work; do not authorize a production four-worker AMX design without integrated contention and FPGA-feed measurements.”

8. **Require independent recomputation before the decision package is closed.**

   The analysis names raw traces, JSON, `exec/r0-analyze.py`, and `exec/r0-g0.py` at p0-trace.html lines 439–441.

   `context_start_text`: `Analysis`  
   `context_end_text`: `Raw JSON next to the traces`

   A reviewer other than the capturing session should reproduce, from raw artifacts:

   - step selection and warmup exclusion;
   - layer/step alignment;
   - `stall_topk_read` extraction;
   - `A_corr` aggregation;
   - CPU cost selection and layer multiplication;
   - bootstrap rows;
   - the closure relation on a sample of layers;
   - all four 20b and four 120b result rows.

   This is warranted because the correction and residual composition were developed after capture. It need not block the conceptual deviation endorsement, but it should block final closure of G0 or expenditure on P1b.

9. **A targeted re-capture is advisable, but P1a instrumented capture is more decision-relevant than repeating the unchanged FPGA baseline.**

   The current marker already captures the corrected boundary over hundreds of 20b steps, and the causal closure is strong. Repeating the same FPGA baseline solely to call the boundary “pre-registered this time” adds procedural cleanliness but limited new information.

   The higher-value verification is to pre-register the corrected boundary and counterfactual timestamps before an instrumented P1a spike, then measure the actual CPU-world residual. Required boundaries should include CPU compute start/end, logits publish, helper entry, helper top-k completion, output publish, and worker-0 read return.

   A small baseline re-capture is still appropriate if independent recomputation reveals ambiguity, marker nesting problems, or unstable per-layer alignment. For 120b 1u/2K specifically, six steps are insufficient for a strong positive or near-threshold conclusion, but that cell is negative already; more samples are needed only if jhan wants a precise 120b performance characterization.

10. **Recommended sequencing and final package language.**

   Use this order:

   1. Independent raw-trace recomputation.
   2. Close 20b G0 as deviation-endorsed PROCEED.
   3. Run the mixed host/device generated-TP compile-and-run spike.
   4. Instrument and execute minimal P1a same-binary FPGA-vs-host A/B.
   5. Evaluate actual `E`, helper contention, top-k residual, expert-launch delay, and FPGA starvation.
   6. Only then decide whether P1b/AMX plumbing is justified.
   7. Treat 120b four-worker AMX as a separate conditional experiment, not as established G0 benefit.

   Suggested consolidated decision entry:

   > **GATE DEVIATION — ENDORSED.** The registered marker failed to operationalize its recorded intent, “the serial cost actually paid”: worker 0’s logits-channel read is nonblocking, while the router-dependent serial block occurs one statement later at the top-k-output read. Code mechanics and trace closure support the minimal corrected boundary. The registered STOP result remains reported; the corrected result remains labeled deviation.  
   >  
   > **20b:** G0 PROCEED to an instrumented P1a host-router spike; all four corrected configurations clear 1% with substantial adverse-sensitivity margin. Do not begin P1b solely from this prediction.  
   >  
   > **120b:** literal G0 non-STOP but conditional only. Single-core results are negative at 1u, above threshold only at 8u/2K, and below threshold at 8u/8K. Four-worker AMX is not used to pass G0 because its end-to-end benefit and contention effects are estimated.  
   >  
   > Before G0 closure, independently reproduce the corrected tables from raw traces. P1a shall pre-register and directly mark the CPU-world dependency boundaries; its integrated measurement supersedes the residual estimate. The current alternate residual row is a reduced-overlap sensitivity, not a maximally conservative bound.
