import contextlib
import os
import signal
import shutil
import dataclasses
from typing import TypedDict
from concurrent.futures import ProcessPoolExecutor, Future
from multiprocessing import Queue
import json
import time
import logging
import numpy as np
import openai
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    SpinnerColumn,
    TaskID,
)
import talos
from testlib.prompt import PromptGenerator
from pprint import pprint
import traceback


logging.getLogger("httpx").setLevel(logging.WARNING)


class TpsGoal(TypedDict):
    mean: float
    min: float


class TpsSample(TypedDict):
    ttft: int
    tps: float


class TpsUpdate(TypedDict):
    worker: int
    phase: str
    intermediate: bool
    advance: int
    tps: float|None


class TpsGoalFailed(Exception):
    pass


@dataclasses.dataclass
class BenchmarkResult:
    """Aggregated per-request results from a benchmark_tps run.

    ttfts/tpss are per-(user, round) lists. prompt_tokens/cached_tokens are the
    server-reported counts per request — prompt_tokens is the exact prefilled
    size (incl. chat template); cached_tokens are prefix-cache hits.
    """
    ttfts: list[float]
    tpss: list[float]
    test_passed: bool
    prompt_tokens: list[int] = dataclasses.field(default_factory=list)
    cached_tokens: list[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Config:
    openai_host: str = dataclasses.field(default_factory=lambda: os.environ['OPENAI_HOST'])
    openai_token: str = dataclasses.field(default_factory=lambda: os.environ['OPENAI_TOKEN'])
    n_users: int = int(os.environ.get('N_USERS', 1))
    n_rounds: int = int(os.environ.get('N_ROUNDS', 1))
    stagger_delay: float = float(os.environ.get('STAGGER_DELAY', 0.1))
    model: str = os.environ.get('MODEL', 'llama-3.1-8b-instruct-good-tp2')
    tokenizer_model: str = os.environ.get('TOKENIZER_MODEL', 'neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16')
    shared_prompt_length: int = int(os.environ.get("SHARED_PROMPT_LENGTH", 0))
    prompt_length: int = int(os.environ.get("PROMPT_LENGTH", 1024))
    generate_length: int = int(os.environ.get("GENERATE_LENGTH", 1152))
    start_capture: int = int(os.environ.get('START_CAPTURE', 896))
    end_capture: int = int(os.environ.get('END_CAPTURE', 1024))
    sample_interval: int = int(os.environ.get('SAMPLE_INTERVAL', 16))
    continuous_usage: int = int(os.environ.get('CONTINUOUS_USAGE', '1'))
    max_tokens: int = None
    goals: dict[str, TpsGoal] = dataclasses.field(default_factory=lambda: json.loads(os.environ.get('TPS_GOALS', json.dumps({
        'llama-3.1-8b-instruct-good-tp2' : {'mean': 144.00, 'min': 140.00},
        'llama-3.2-3b-instruct-fast-tp2' : {'mean': 191.00, 'min': 150.00},
        'llama-3.3-70b-instruct-good-tp2': {'mean': 27.00,  'min': 27.00},
        'mixtral-8x7b-instruct-v0.1-tp2' : {'mean': 80.00,  'min': 80.00},
        'llama-3.3-70b-instruct-good-tp4': {'mean': 27.00, 'min': 27.00},
        'qwen-2.5-32b-it-fast-tp2' : {'mean': 35.00, 'min': 35.00},
        'ingested-qwen-3-4b-instruct-2507-tp2' : {'mean': 195.00, 'min': 170.00},
        'ingested-qwen-3-4b-instruct-2507-tp4' : {'mean': 160.00, 'min': 125.00},
        'gemma-2-9b-it-fast-tp2' : {'mean': 90.00, 'min': 90.00},
        'ingested-gpt-oss-120b-tp4' : {'mean': 77.00, 'min': 77.00},
        'ingested-gemma-4-31b-it-tp2' : {'mean': 1.00, 'min': 1.00},
    }))))

    def __post_init__(self):
        if self.max_tokens is None:
            self.max_tokens = int(os.environ.get('MAX_TOKENS', self.generate_length))


@dataclasses.dataclass
class Worker:
    config: Config
    prompt_generator: PromptGenerator
    index: int
    group_queue: Queue
    ingress: Queue = dataclasses.field(default_factory=Queue)
    egress: Queue = dataclasses.field(default_factory=Queue)
    future: Future = None

    def sync(self):
        while 1:
            try:
                return self.egress.get(timeout=1)
            except Exception:
                if self.future.done():
                    exc = self.future.exception()
                    if exc:
                        talos.session.log.error(
                            f"Worker {self.index} failed during sync\n"
                            f"Model: {self.config.model}\n"
                            f"Exception type: {type(exc).__name__}\n"
                            f"Exception message: {str(exc)}"
                        )
                        talos.session.log.error(f"Traceback:\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))}")
                    raise exc from None


workers: list[Worker] = []


def run_tps_worker(index: int):
    wkr = workers[index]
    for round_index in range(wkr.config.n_rounds):

        wkr.egress.put({'op': 'ready'})
        wkr.ingress.get()
        # TODO: generate prompt

        prompt = wkr.prompt_generator.generate(
            prompt_length=wkr.config.prompt_length,
            seed=round_index * wkr.config.n_users + index,
        )

        wkr.egress.put({'op': 'ready'})
        wkr.ingress.get()

        sample = get_tps_sample(wkr.config, prompt, index, round_index, wkr.group_queue)
        wkr.group_queue.put({'worker': index, 'op': 'sample', **sample})


def benchmark_tps(config: Config, raise_for_goal=True):
    with contextlib.suppress(Exception):
        shutil.rmtree(".perf")
    os.mkdir(".perf")
    pprint(config)
    talos.session.graph({
        "name": f"TPS - {config.model} @ {config.n_users} users",
        "chartType": "line",
        "xAxis": "timestamp",
        "yAxis": "tps",
        "datasets": "sample",
        "filters": [
            { "key": "type", "value": "tps" },
            { "key": "model", "value": config.model },
            { "key": "n_users", "value": str(config.n_users) },
        ],
    })
    talos.session.graph({
        "name": f"TTFT - {config.model} @ {config.n_users} users",
        "chartType": "bar",
        "xAxis": "round",
        "yAxis": "ttft",
        "datasets": "user",
        "filters": [
            { "key": "type", "value": "ttft" },
            { "key": "model", "value": config.model },
            { "key": "n_users", "value": str(config.n_users) },
        ],
    })
    talos.session.graph({
        "name": f"Prefill (TTFT-derived) - {config.model} @ {config.n_users} users",
        "chartType": "bar",
        "xAxis": "round",
        "yAxis": "prefill",
        "datasets": "user",
        "filters": [
            { "key": "type", "value": "ttft" },
            { "key": "model", "value": config.model },
            { "key": "n_users", "value": str(config.n_users) },
        ],
    })
    global workers
    prompt_generator = PromptGenerator.for_model(config.tokenizer_model)
    group_queue = Queue()
    workers = [Worker(config, prompt_generator, user_index, group_queue) for user_index in range(config.n_users)]
    ttfts: list[float] = []
    tpss: list[float] = []
    prompt_tokens_list: list[int] = []
    cached_tokens_list: list[int] = []
    ttft = None
    tps = None
    goal = config.goals.get(config.model)
    min_tps = None
    test_passed = True
    tasks: dict[int, TaskID] = {}
    def _reset_sigterm():
      signal.signal(signal.SIGTERM, signal.SIG_DFL)

    with ProcessPoolExecutor(max_workers=config.n_users, initializer=_reset_sigterm) as executor:
        try:
            for wkr in workers:
                wkr.future = executor.submit(run_tps_worker, wkr.index)
            for round_index in range(config.n_rounds):

                # sync start
                for wkr in workers:
                    wkr.sync()

                talos.session.log.info(f"Running round ({round_index + 1}/{config.n_rounds})")

                # run prepare
                for wkr in workers:
                    wkr.ingress.put({'op': 'prepare'})

                # sync prepare
                for wkr in workers:
                    wkr.sync()

                # run test
                for wkr in workers:
                    wkr.ingress.put({'op': 'run'})

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    MofNCompleteColumn(),
                    TextColumn("tokens"),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                ) as progress:

                    desc_width = 50
                    for wkr in workers:
                        tasks[wkr.index] = progress.add_task(f"[gray](User {wkr.index}) Pending".ljust(desc_width, " "), total=config.generate_length)

                    # get samples
                    pending: list[Worker] = [*workers]
                    wkr_map = {wkr.index: wkr for wkr in workers}
                    while len(pending) > 0:
                        try:
                            sample = group_queue.get(timeout=1)
                        except Exception:
                            for wkr in pending:
                                if wkr.future.done():
                                    exc = wkr.future.exception()
                                    if exc:
                                        talos.session.log.error(
                                            f"Worker {wkr.index} failed during round {round_index + 1}/{config.n_rounds}\n"
                                            f"Model: {config.model}\n"
                                            f"Exception type: {type(exc).__name__}\n"
                                            f"Exception message: {str(exc)}\n"
                                            f"Worker config: n_users={config.n_users}, n_rounds={config.n_rounds}, "
                                            f"prompt_length={config.prompt_length}, generate_length={config.generate_length}"
                                        )
                                        talos.session.log.error(f"Traceback:\n{traceback.format_exc()}")
                                        raise exc from None
                            continue
                        wkr = wkr_map[sample['worker']]
                        if 'intermediate' not in sample:
                            ttfts.append(sample['ttft'])
                            tpss.append(sample['tps'])
                            prompt_tokens_list.append(sample.get('prompt_tokens', 0))
                            cached_tokens_list.append(sample.get('cached_tokens', 0))
                            color = 'red' if (sample['tps'] < goal['min']) else 'cyan'
                            desc = f"[{color}]Done (TTFT={sample['ttft']}, {sample['tps']:.2f} / {goal['min']:.2f} TPS)".ljust(desc_width, " ")
                            progress.update(tasks[wkr.index], description=desc)
                            if not min_tps or sample['tps'] < min_tps:
                                min_tps = sample['tps']
                            for talos_sample in sample.pop('talos_samples', []):
                                talos.session.sample(**talos_sample)
                            if wkr in pending:
                                pending.remove(wkr)
                            continue
                        data: TpsUpdate = sample
                        desc = "Unknown".ljust(desc_width, " ")
                        if data['phase'] == "gen":
                            desc = f"[green](User {wkr.index}) Generating"
                            if data['tps'] is not None:
                                desc += f" ({data['tps']:.2f} TPS)"
                        elif data['phase'] == "parse":
                            desc = f"[cyan](User {wkr.index}) Parsing prompt".ljust(desc_width, " ")
                        progress.update(
                            tasks[wkr.index],
                            description=desc.ljust(desc_width, " "),
                            advance=data['advance'],
                        )
                ttft = int(np.mean(ttfts))
                tps = round(np.mean(tpss), 2)
                talos.session.log.info(f"Running averages: TTFT={ttft}, TPS={tps}")

        finally:
            executor.shutdown(wait=False, cancel_futures=True)
    if goal and (min_tps < goal['min'] or tps < goal['mean']) and raise_for_goal:
        test_passed = False
        if raise_for_goal:
            raise TpsGoalFailed(f"TPS={tps}, Min TPS={min_tps} (Goal: TPS={goal['mean']}, Min TPS={goal['min']})")
    return BenchmarkResult(
        ttfts=ttfts,
        tpss=tpss,
        test_passed=test_passed,
        prompt_tokens=prompt_tokens_list,
        cached_tokens=cached_tokens_list,
    )


class StopOverrideFailed(Exception):
    pass


def _ttft_sample_metrics(first_chunk, prompt_length: int, ttft: int):
    """Server token accounting + TTFT-derived prefill for the ttft sample.

    prompt_tokens / cached_tokens come from the first chunk's usage (present
    under include_continuous_usage), falling back to the configured prompt_length
    when usage is absent. prefill uses the configured prompt_length as numerator
    (a stable TTFT proxy). Returns (prompt_tokens, cached_tokens, prefill).
    """
    prompt_tokens = prompt_length
    cached_tokens = 0
    usage = getattr(first_chunk, 'usage', None)
    if usage:
        prompt_tokens = usage.prompt_tokens or prompt_tokens
        details = usage.prompt_tokens_details
        if details and details.cached_tokens:
            cached_tokens = details.cached_tokens
    prefill = prompt_length / (ttft / 1000.0) if ttft else 0
    return prompt_tokens, cached_tokens, prefill


def get_tps_sample(config: Config, prompt: list, user_index: int, round_index: int, queue: Queue) -> TpsSample:
    root_dir = f".perf/round_{round_index}/user_{user_index}"
    os.makedirs(root_dir, exist_ok=True)
    tps = None
    talos_samples = []
    update: TpsUpdate = {
        'worker': user_index,
        'intermediate': True,
        'advance': 0,
        'tps': tps,
        'phase': 'parse',
    }
    time.sleep(user_index * config.stagger_delay)
    queue.put(update)

    sample = f'user={user_index}, round={round_index}'
    client = openai.OpenAI(
        base_url=config.openai_host,
        api_key=config.openai_token
    )
    sequence = []
    start_time = time.perf_counter()
    # log.info(f"PROMPT:\n{self.prompt}")
    stream = iter(client.chat.completions.create(
        max_tokens  = config.max_tokens,
        stream      = True,
        model       = config.model,
        messages    = prompt,
        stop        = None,
        extra_body={
            "ignore_eos": True,
        },
        stream_options={"include_usage": True, "include_continuous_usage": True}
    ))
    first_chunk = next(stream)
    parse_time = time.perf_counter()
    token = first_chunk.choices[0].delta.content if first_chunk.choices else None
    if token: sequence.append(token)
    ttft = int((parse_time - start_time) * 1000)
    # Server token accounting (observability) + TTFT-derived prefill. See helper.
    prompt_tokens, cached_tokens, prefill = _ttft_sample_metrics(
        first_chunk, config.prompt_length, ttft
    )
    talos_samples.append(dict(
        type = 'ttft',
        model = config.model,
        n_users = str(config.n_users),
        ttft = ttft,
        prefill = prefill,
        prompt_tokens = prompt_tokens,
        cached_tokens = cached_tokens,
        prompt_length = config.prompt_length,
        user = user_index,
        round = round_index,
        sample = sample,
        timestamp = time.time(),
    ))
    update['advance'] = 1
    update['phase'] = 'gen'
    queue.put(update)
    prev_sample_time = 0.0
    capture_duration = 0
    current_token_count = 0
    last_token_count = 0
    last_sampled_token = config.start_capture
    samples_taken = 0
    capture_start = 0
    sequence_length = 0
    chunks = []
    prev_chunk_time = 0.0
    burst_count = 0  # chunks arriving <0.1ms apart in capture window
    capture_chunk_deltas = []  # (token_jump, inter_arrival_ms) for chunks in capture window
    for chunk in stream:
        chunks.append(chunk)
        if config.continuous_usage:
            if chunk.usage and chunk.usage.completion_tokens > 0:
                current_token_count = chunk.usage.completion_tokens
                sequence_length = chunk.usage.total_tokens
            elif not (chunk.choices and chunk.choices[0].finish_reason):
                print(f"\n\n(user {user_index}) round {round_index}, no valid usage_data\n\n\n")
        else:
            current_token_count = len(sequence)
            sequence_length = config.shared_prompt_length + config.prompt_length + current_token_count
        if len(chunk.choices) == 0:
            continue
        token = chunk.choices[0].delta.content
        if token:
            sequence.append(token)
        if config.continuous_usage:
            if chunk.usage:
                current_token_count = chunk.usage.completion_tokens
        else:
            current_token_count = len(sequence)
        # Track chunk timing in the capture window
        chunk_time = time.perf_counter()
        if capture_start > 0 and capture_duration == 0:
            token_jump = current_token_count - last_token_count
            inter_arrival_ms = (chunk_time - prev_chunk_time) * 1000 if prev_chunk_time > 0 else 0
            capture_chunk_deltas.append((token_jump, inter_arrival_ms))
            if inter_arrival_ms < 0.1 and prev_chunk_time > 0:
                burst_count += 1
        prev_chunk_time = chunk_time

        if current_token_count == config.start_capture:
            capture_start = time.perf_counter()
        elif current_token_count > config.start_capture and capture_start == 0:
            capture_start = time.perf_counter()
            last_sampled_token = current_token_count
        elif current_token_count >= config.end_capture and capture_duration == 0:
            capture_duration = time.perf_counter() - capture_start
        if current_token_count <= config.end_capture and (current_token_count >= config.sample_interval + last_sampled_token):
            sample_time = time.perf_counter()
            samples_taken += 1
            if prev_sample_time > 0.0:
                sample_duration = sample_time - prev_sample_time
                token_count_delta = current_token_count - last_sampled_token
                tps = token_count_delta / sample_duration
                if tps > 1000:
                    recent_arrivals = [round(d[1], 3) for d in capture_chunk_deltas[-token_count_delta:]]
                    talos.session.log.error(
                        f"(user {user_index} round {round_index} sample {samples_taken}) "
                        f"anomalous tps={tps:.1f}, tokens={token_count_delta} in {sample_duration:.6f}s, "
                        f"token_at={current_token_count}/{config.end_capture}, "
                        f"burst_so_far={burst_count}, "
                        f"recent_inter_arrival_ms={recent_arrivals}"
                    )
                #print(f"\n(user {user_index}) round {round_index}, new tokens: {token_count_delta}, sample_duration: {sample_duration}, tps: {tps}\n")
                #print(f"(user {user_index}) round {round_index}, current_token_count: {current_token_count}, config.end_capture: {config.end_capture}, config.sample_interval: {config.sample_interval}, tps: {tps}\n")
                talos_samples.append(dict(
                    type = 'tps',
                    model = config.model,
                    n_users = str(config.n_users),
                    sequence_length = sequence_length,
                    tps = tps,
                    user = user_index,
                    round = round_index,
                    sample = sample,
                    timestamp = time.time(),
                ))
                update['tps'] = tps
            last_sampled_token = current_token_count
            prev_sample_time = sample_time
        update['advance'] = current_token_count - last_token_count
        last_token_count = current_token_count
        queue.put(update)
    with open(f"{root_dir}/prompt.json", "w") as f:
        f.write(json.dumps(prompt, indent=4))
    with open(f"{root_dir}/chunks.txt", "w") as f:
        for chunk in chunks:
            f.write(f"{chunk}\n")
    if current_token_count < config.generate_length:
        raise StopOverrideFailed(f"Target stopped token generation ({current_token_count}/{config.generate_length} generated), despite being explicitly asked to keep going")
    if capture_duration == 0:
        raise StopOverrideFailed(f"\n(user {user_index}) round {round_index}, No capture duration, capture_duration: {capture_duration}\n\n\n")
    tps = (config.end_capture - config.start_capture) / capture_duration

    # Diagnostic logging for TPS measurement quality
    expected_tps = config.goals.get(config.model, {}).get('mean', 0)
    is_suspicious = expected_tps > 0 and tps > expected_tps * 2
    if is_suspicious or burst_count > 10:
        sample_tps_values = [
            s['tps'] for s in talos_samples
            if s.get('type') == 'tps' and s.get('round') == round_index and s.get('user') == user_index
        ]
        median_sample_tps = sorted(sample_tps_values)[len(sample_tps_values) // 2] if sample_tps_values else 0
        expected_duration = f"{(config.end_capture - config.start_capture) / expected_tps:.3f}s" if expected_tps > 0 else "n/a"
        tps_ratio = f"{tps / expected_tps:.1f}x" if expected_tps > 0 else "n/a"
        print(
            f"\n[TPS DIAGNOSTIC] user={user_index} round={round_index} model={config.model}\n"
            f"  capture_duration={capture_duration:.6f}s  (expected ~{expected_duration})\n"
            f"  reported_tps={tps:.1f}  expected_tps={expected_tps:.1f}  ratio={tps_ratio}\n"
            f"  median_sample_tps={median_sample_tps:.1f}  (intermediate samples from this round)\n"
            f"  burst_chunks={burst_count}/{len(capture_chunk_deltas)} in capture window (<0.1ms apart)\n"
            f"  token_jumps={[d[0] for d in capture_chunk_deltas[:20]]}{'...' if len(capture_chunk_deltas) > 20 else ''}\n"
            f"  inter_arrival_ms={[round(d[1], 3) for d in capture_chunk_deltas[:20]]}{'...' if len(capture_chunk_deltas) > 20 else ''}\n"
        )

    return {
        'ttft': ttft,
        'tps': tps,
        'prompt_tokens': prompt_tokens,
        'cached_tokens': cached_tokens,
        'talos_samples': talos_samples,
    }
