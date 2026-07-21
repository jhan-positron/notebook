#!/usr/bin/env python3
"""loadgen.py — talos-style closed-loop load generator for the rinzler path.
Stdlib only. N concurrent users, each looping streamed /v1/completions
requests against a list of rinzler endpoints (round-robin per user).
Records per-request TTFT + decode rate from SSE chunk timestamps, and true
window aggregate (makespan-based), per the 2026-07-12 metrics consensus.

Usage:
  python3 loadgen.py --endpoints host:port[,host:port...] --model NAME \
      --users 8 --prompt-chars 4000 --max-tokens 256 --duration 900 \
      --out /path/results.jsonl [--label armA]

Metrics reported (talos-comparable):
  DEFAULT decode metric (since 2026-07-21, per jhan's directive): the CI
  capture window — decode TPS = (capture_end - capture_start) / (time
  from token #capture_start to token #capture_end), defaults 896-1024,
  exactly tps.py's formula. The whole-generation rate
  ((tokens-1)/(t_last - t_first)) is still reported as
  decode_tps_whole_* — all loadgen results BEFORE 2026-07-21 (ab30-ab34)
  used the whole-generation metric, which reads ~2-3pp HIGHER; compare
  old runs against decode_tps_whole_*, not the capture numbers.
  TTFT = send -> first SSE token. Aggregate = total output tokens /
  measurement window. Requests that never reach capture_end are counted
  in capture_incomplete and excluded from the capture metric.
"""
import argparse, http.client, json, threading, time, statistics, sys, random

STOP = threading.Event()

def make_prompt(nchars, rng):
    # UNIQUE per request: a shared identical prompt would hit tron's KV
    # prefix cache and skip nearly all prefill work (verified: TTFT 92ms
    # vs ~1.3s for a real 1k-token prefill). Random word salad per call.
    words = ("the quick brown fox jumps over the lazy dog while carefully "
             "measuring inference throughput across concurrent user streams "
             "alpha bravo charlie delta echo foxtrot golf hotel india juliet "
             "kilo lima mike november oscar papa quebec romeo sierra tango ").split()
    out = [f"session {rng.getrandbits(64):x}:"]
    n = len(out[0])
    while n < nchars:
        w = rng.choice(words)
        out.append(w); n += len(w) + 1
    return " ".join(out)

def one_request(host, port, model, prompt, max_tokens, cap_start, cap_end, timeout=600):
    rec = {"host": f"{host}:{port}", "t_send": time.time(), "tokens": 0,
           "t_first": None, "t_last": None, "error": None,
           "t_cap_start": None, "t_cap_end": None}
    try:
        c = http.client.HTTPConnection(host, port, timeout=timeout)
        # /v1/chat/completions streams one SSE event per token (verified
        # 2026-07-13); raw /v1/completions does NOT stream per-token and
        # surfaces no text for harmony-format models like gpt-oss.
        # ignore_eos + continuous usage match the CI harness (tps.py sends
        # both, always). ignore_eos guarantees the capture window completes;
        # continuous usage is the AUTHORITATIVE token counter — rinzler
        # coalesces ~2 tokens per SSE event for fast models (measured on
        # llama-8b 2026-07-21: 1100 tokens in ~600 events), so counting
        # events undercounts. gpt-oss at ~90-105 t/s streams 1:1, which is
        # why pre-2026-07-21 event-counted gpt-oss numbers remain valid.
        body = json.dumps({"model": model,
                           "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": max_tokens, "temperature": 0,
                           "stream": True, "ignore_eos": True,
                           "stream_options": {"include_usage": True,
                                              "include_continuous_usage": True}})
        c.request("POST", "/v1/chat/completions", body=body,
                  headers={"Content-Type": "application/json"})
        r = c.getresponse()
        if r.status != 200:
            rec["error"] = f"http {r.status}: {r.read(200)!r}"
            return rec
        buf = b""
        while True:
            chunk = r.read1(65536)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if data == b"[DONE]":
                    c.close()
                    return rec
                now = time.time()
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                usage = obj.get("usage") or {}
                ct = usage.get("completion_tokens")
                if ct:
                    new_tokens = ct
                else:
                    # fallback when the server sends no continuous usage:
                    # count content-bearing events (1:1 only for slow models)
                    ch = obj.get("choices") or []
                    delta = (ch[0].get("delta") if ch else {}) or {}
                    new_tokens = rec["tokens"] + (1 if delta.get("content") else 0)
                if new_tokens > rec["tokens"]:
                    rec["tokens"] = new_tokens
                    if rec["t_first"] is None:
                        rec["t_first"] = now
                    rec["t_last"] = now
                    # CI capture window (tps.py semantics): clock starts at
                    # token #cap_start, stops at token #cap_end.
                    if rec["t_cap_start"] is None and rec["tokens"] >= cap_start:
                        rec["t_cap_start"] = now
                    elif rec["t_cap_end"] is None and rec["t_cap_start"] is not None \
                            and rec["tokens"] >= cap_end:
                        rec["t_cap_end"] = now
        c.close()
    except Exception as e:
        rec["error"] = repr(e)
    return rec

def user_loop(uid, endpoints, model, prompt_chars, max_tokens, out, lock, t_end,
              cap_start, cap_end, shared_prefix="", think_time=0.0):
    ep = endpoints[uid % len(endpoints)]
    host, port = ep.split(":")
    # time-salted: deterministic seeds made runs replay identical prompt
    # sequences, which tron's PERSISTENT token cache served as prefix hits
    # (TTFT 1.23s -> 0.135s across runs, 2026-07-13). Salt per process run.
    rng = random.Random(hash((uid, time.time_ns())))
    tail_chars = max(prompt_chars - len(shared_prefix), 120)
    while not STOP.is_set() and time.time() < t_end:
        prompt = (shared_prefix + " " if shared_prefix else "") + make_prompt(tail_chars, rng)
        rec = one_request(host, int(port), model, prompt, max_tokens, cap_start, cap_end)
        rec["user"] = uid
        with lock:
            out.append(rec)
            print(json.dumps(rec), file=OUTF, flush=True)
        if think_time > 0:
            time.sleep(think_time)

def main():
    global OUTF
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--users", type=int, default=8)
    ap.add_argument("--prompt-chars", type=int, default=4000)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--duration", type=int, default=900)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--shared-prefix-chars", type=int, default=0,
                    help="build a FIXED prefix (seed 777, identical across "
                         "runs) of this many chars + unique tail — exercises "
                         "the persistent prefix cache like a templated corpus")
    ap.add_argument("--think-time", type=float, default=0.0,
                    help="seconds each user sleeps between requests")
    ap.add_argument("--capture-start", type=int, default=896,
                    help="decode metric clock starts at this token (CI default 896)")
    ap.add_argument("--capture-end", type=int, default=1024,
                    help="decode metric clock stops at this token (CI default 1024)")
    a = ap.parse_args()
    if a.max_tokens < a.capture_end:
        print(f"WARNING: max_tokens {a.max_tokens} < capture_end {a.capture_end} — "
              f"no request can complete the capture window; decode metric will "
              f"fall back to whole-generation", file=sys.stderr)

    shared_prefix = ""
    if a.shared_prefix_chars > 0:
        shared_prefix = make_prompt(a.shared_prefix_chars, random.Random(777))

    endpoints = a.endpoints.split(",")
    OUTF = open(a.out, "w")
    out, lock = [], threading.Lock()
    t_start = time.time(); t_end = t_start + a.duration
    threads = [threading.Thread(target=user_loop,
               args=(u, endpoints, a.model, a.prompt_chars, a.max_tokens, out, lock, t_end,
                     a.capture_start, a.capture_end, shared_prefix, a.think_time),
               daemon=True) for u in range(a.users)]
    for t in threads: t.start()
    try:
        for t in threads: t.join()
    except KeyboardInterrupt:
        STOP.set()
    t_done = time.time()
    OUTF.close()

    ok = [r for r in out if not r["error"] and r["tokens"] > 2 and r["t_first"]]
    err = [r for r in out if r["error"]]
    if not ok:
        print(json.dumps({"label": a.label, "error": "no successful requests",
                          "failures": len(err)})); sys.exit(1)
    per_user_whole, per_user_cap = {}, {}
    cap_incomplete = 0
    cap_tokens = a.capture_end - a.capture_start
    for r in ok:
        r["decode_tps_whole"] = (r["tokens"] - 1) / max(r["t_last"] - r["t_first"], 1e-9)
        r["ttft"] = r["t_first"] - r["t_send"]
        per_user_whole.setdefault(r["user"], []).append(r["decode_tps_whole"])
        if r["t_cap_start"] and r["t_cap_end"]:
            r["decode_tps_capture"] = cap_tokens / max(r["t_cap_end"] - r["t_cap_start"], 1e-9)
            per_user_cap.setdefault(r["user"], []).append(r["decode_tps_capture"])
        else:
            cap_incomplete += 1
    user_whole = {u: statistics.mean(v) for u, v in per_user_whole.items()}
    total_tokens = sum(r["tokens"] for r in ok)
    window = t_done - t_start
    summary = {
        "label": a.label, "model": a.model, "users": a.users,
        "endpoints": endpoints, "requests_ok": len(ok), "requests_err": len(err),
        "prompt_chars": a.prompt_chars, "max_tokens": a.max_tokens,
        "window_s": round(window, 1),
        "capture_window": f"{a.capture_start}-{a.capture_end}",
        "capture_incomplete": cap_incomplete,
        "ttft_mean_s": round(statistics.mean(r["ttft"] for r in ok), 3),
        "ttft_p95_s": round(sorted(r["ttft"] for r in ok)[int(0.95 * len(ok)) - 1], 3),
        "aggregate_output_tps_makespan": round(total_tokens / window, 1),
        "decode_tps_whole_mean": round(statistics.mean(user_whole.values()), 2),
        "decode_tps_whole_slowest_user": round(min(user_whole.values()), 2),
    }
    if per_user_cap:
        user_cap = {u: statistics.mean(v) for u, v in per_user_cap.items()}
        # DEFAULT metric (CI-comparable capture window, tps.py formula)
        summary["decode_tps_per_user_mean"] = round(statistics.mean(user_cap.values()), 2)
        summary["decode_tps_slowest_user"] = round(min(user_cap.values()), 2)
    else:
        # fall back to whole-generation, keeping the historical key names
        summary["decode_metric_fallback"] = "whole-generation (no request completed the capture window)"
        summary["decode_tps_per_user_mean"] = summary["decode_tps_whole_mean"]
        summary["decode_tps_slowest_user"] = summary["decode_tps_whole_slowest_user"]
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
