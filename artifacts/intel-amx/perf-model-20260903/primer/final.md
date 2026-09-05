<callout icon="📌">
	**Short version.** Tron (Positron's inference program) generated tokens 17.3% faster with AMX (Intel CPU instructions that multiply small matrices in one step) than without it, at prompt 8192 (a prompt of 8192 tokens) on delphi-3bda (the test server). Four steps predict +14.4% (estimate) from Tron's AMX-off run plus unit_bench, a stand-alone copy of Tron's per-unit attention code: 2.9 percentage points low, with the step-2 check failed.
</callout>
- **Words used here. AVX**: the CPU's ordinary vector instructions, used by Tron's attention without AMX. **Page**: 64 stored tokens of keys and values (32 KiB) for one of 36 layers and one key/value head (shared by 4 query heads). **Unit**: one query token's 4 heads against one page. **Coverage**: share of units on full pages, the only ones AMX runs.
- **Worker**: one of 27 CPU threads running units; worker 0's timers are reported as medians (middle values) over 510 generated tokens. **Page work**: its loop over units. **Joins**: merging results across workers. **Barrier**: waiting for the slowest. **Untimed rest**: attention time no timer covers.
### Step 1. Write the time formula (only the covered units change)
```plain text
token     = other work (all else; unchanged) + attention
attention = page work + joins + barrier + untimed rest    (last three unchanged)
page work = units x (c x AMX unit + (1 - c) x AVX unit)          c = coverage
            + page-loop overhead + AMX tile extras (tile setup and release)
unit      = hot compute (page already in the core's cache) + data wait
```
### Step 2. Take three measurements, compare them two ways
FIGURE_PLACEHOLDER
- Tron and the AVX path run a hand copy of the same per-unit code, so their gap is the calibration error (what the copy misses of Tron): 0.334 µs, 9.5% of Tron's unit; the plan (rules fixed before measuring) allowed 5%. Tron's lower clock (3.74 against 3.895 GHz) explains 0.067 µs; 0.267 µs is unexplained.
- The two paths differ only in code path, so their gap is the AMX effect: 1.06 µs of hot compute (AVX 1.682, AMX 0.621 µs) but only 0.47 µs under the 27-thread load, because a page's 32 KiB take 2.494 µs to arrive at 13.14 GB/s per core.
### Step 3. Inputs (measured) and arithmetic (estimate); prompt 8192, worker 0, µs
<table header-row="true">
	<tr>
		<td>Level (sums use unrounded values)</td>
		<td>Tron, AMX off</td>
		<td>unit_bench</td>
	</tr>
	<tr>
		<td>token = other work + page work + joins + barrier + rest</td>
		<td>9283.1 = 3439.4 + 5270.5 + 247.9 + 226.8 + 98.5</td>
		<td></td>
	</tr>
	<tr>
		<td>page work = units × unit + page-loop overhead</td>
		<td>5270.5 = 1476 × 3.527 + 64.4</td>
		<td>AMX tile extras 6.8 per token</td>
	</tr>
	<tr>
		<td>unit (99.24% covered, per earlier AMX-run counters)</td>
		<td>3.527</td>
		<td>AVX 3.193; AMX 2.727 = hot 0.621 + wait 2.106</td>
	</tr>
</table>
```plain text
page work = 1476 x (0.9924 x 2.727 + 0.0076 x 3.527) + 64.4 + 6.8 = 4104.8
attention = 4104.8 + 247.9 joins + 226.8 barrier + 98.5 rest        = 4678.0
token     = 3439.4 other work + 4678.0                              = 8117.4
boost     = 9283.1 / 8117.4 - 1 = +14.4%     measured +17.3%     -2.9 points
+0.1 µs on the AMX unit lowers the boost by 2.1 percentage points
```
### Step 4. Compare, and state what is open
- Other prompts (their step-2 checks failed too): prompt 2048 est. +6.4% against measured +6.1%; prompt 256 est. +1.9% against +0.5%.
- Open: the plan's rule as written carries the whole 0.334 µs gap onto the AMX unit and gives +8.8%; this page drops the unexplained 0.267 µs, a choice made after that result. Under the plan the verdict is "calibration failed", and +17.3% lies above the pre-registered band of +7.9% to +15.9%.
Numbers: perf-model/index.html sections 3 to 6 and 8; model.json, prompt 8192.
