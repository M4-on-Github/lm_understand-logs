"""Runner for Experiment 1 ("which game?") with Claude models.

One fresh conversation per network, one reply, no tools. See exp01_which_game_plan.md.

Usage (from the repo root):
  python test-claude/exp01/code/run_exp1.py --check
        load the four prompts and check them against the original loop.log; calls nothing
  python test-claude/exp01/code/run_exp1.py --count-tokens
        count the prompt tokens on both models (free) and write eval/token_counts.json
  python test-claude/exp01/code/run_exp1.py --model claude-opus-5-5 --network a9f535cc
        make one paid call
  python test-claude/exp01/code/run_exp1.py --model all --network all
        make every call that has no run folder yet
  python test-claude/exp01/code/run_exp1.py --replay --runs DIR
        test the runner and log writer with Astra's recorded answers; calls nothing
"""

import argparse
import json
import re
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
ORIGINAL = REPO / "rikiya's_exps" / "exp1_which_game"
sys.path.insert(0, str(REPO / "test-claude" / "common"))

import model_client  # noqa: E402
import runlog  # noqa: E402

MODELS = ["claude-opus-5-5", "claude-fable-5-2"]
EFFORT = "high"
MAX_TOKENS = 64000


def read_lf(path):
    """Read a released text file as it was sent to Astra: UTF-8 with LF line endings.

    A Windows checkout with core.autocrlf=true stores these files with CRLF.
    """
    return Path(path).read_bytes().decode("utf-8").replace("\r\n", "\n")


def original_lengths():
    """Characters sent to Astra per network ID, from the original loop.log."""
    lengths = {}
    for m in re.finditer(r"\] (\w+): asking \(([\d,]+) chars\)", read_lf(ORIGINAL / "runs" / "loop.log")):
        lengths[m.group(1)] = int(m.group(2).replace(",", ""))
    return lengths


def load_prompts():
    """Network ID -> prompt text.

    The released run folders are named by game. To keep game names out of the runner, each prompt is matched
    to its network by content: it must end with that network's weights text. The answer key is not read.
    """
    lengths = original_lengths()
    prompt_files = sorted((ORIGINAL / "runs").glob("*/prompt.txt"))
    texts = [read_lf(p) for p in prompt_files]
    prompts = {}
    for net_id in sorted(lengths):
        weights = read_lf(ORIGINAL / "networks" / f"{net_id}_actor.txt").rstrip("\n")
        matches = [t for t in texts if t.rstrip("\n").endswith(weights)]
        if len(matches) != 1:
            raise SystemExit(f"{net_id}: {len(matches)} prompts end with its weights; expected 1")
        if len(matches[0]) != lengths[net_id]:
            raise SystemExit(
                f"{net_id}: prompt is {len(matches[0]):,} chars, the original loop.log says {lengths[net_id]:,}"
            )
        prompts[net_id] = matches[0]
    return prompts


def system_line():
    files = sorted((ORIGINAL / "runs").glob("*/instructions.md"))
    lines = {read_lf(f).strip() for f in files}
    if len(lines) != 1:
        raise SystemExit("the released instructions.md files differ")
    return lines.pop()


def outcome_of(reply):
    if reply.stop_reason == "refusal":
        return "refused"
    if reply.stop_reason == "max_tokens":
        return "truncated"
    if not reply.tool_free:
        return "tool_use"
    return "ok"


def run_one(client, model, net_id, prompt, system, runs_dir):
    messages = [{"role": "user", "content": prompt}]
    run_dir = runlog.new_run_dir(runs_dir, model, net_id)
    loop_log = Path(runs_dir) / "loop.log"
    index = Path(runs_dir) / "index.jsonl"

    runlog.write_text(run_dir / "prompt.txt", prompt)
    runlog.write_text(run_dir / "instructions.md", system + "\n")
    body = model_client.request_body(model, system, messages, EFFORT, MAX_TOKENS)
    body["messages"] = [{"role": "user", "content": "<see prompt.txt>"}]
    runlog.write_json(run_dir / "request.json", body)

    record = {
        "ok": False,
        "outcome": "error",
        "network_id": net_id,
        "model_requested": model,
        "model_returned": None,
        "effort": EFFORT,
        "max_tokens": MAX_TOKENS,
        "thinking": body["thinking"],
        "prompt_sha256": runlog.sha256_text(prompt),
        "prompt_chars": len(prompt),
        "start": runlog.now(),
        "sdk_version": client.sdk_version,
        "python_version": runlog.python_version(),
        "code_commit": runlog.code_commit(REPO),
        "attempt": 1,
    }
    runlog.append_line(loop_log, f"[{record['start']}] {model} {net_id} {run_dir.name}: asking ({len(prompt):,} chars)")

    stderr = ""
    try:
        reply = client.send(model, system, messages, EFFORT, MAX_TOKENS)
    except Exception:
        stderr = traceback.format_exc()
        record.update({"end": runlog.now(), "wall_s": None, "audit": {"tool_free": None, "usage": {}}})
        runlog.write_text(run_dir / "stderr.log", stderr)
        runlog.write_json(run_dir / "run.json", record)
        runlog.append_line(loop_log, f"[{record['end']}] {model} {net_id} {run_dir.name}: request failed")
        runlog.append_line(index, json.dumps({k: record.get(k) for k in INDEX_KEYS} | {"run_dir": rel(run_dir, runs_dir)}))
        print(stderr, file=sys.stderr)
        return record

    runlog.write_text(run_dir / "events.jsonl", "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in reply.events))
    runlog.write_text(run_dir / "answer.md", reply.text)
    runlog.write_text(run_dir / "stderr.log", "")
    outcome = outcome_of(reply)
    record.update({
        "ok": outcome == "ok",
        "outcome": outcome,
        "model_returned": reply.model_returned,
        "message_id": reply.message_id,
        "request_id": reply.request_id,
        "stop_reason": reply.stop_reason,
        "stop_details": reply.stop_details,
        "end": runlog.now(),
        "wall_s": reply.wall_s,
        "thinking_summaries": reply.thinking,
        "cost_usd": model_client.cost_usd(model, reply.usage),
        "audit": {
            "item_types": reply.block_types,
            "tool_items": reply.tool_blocks,
            "tool_free": reply.tool_free,
            "usage": reply.usage,
        },
    })
    runlog.write_json(run_dir / "run.json", record)
    runlog.append_line(
        loop_log,
        f"[{record['end']}] {model} {net_id} {run_dir.name}: {outcome}, tool-free {reply.tool_free}, "
        f"cost ${record['cost_usd']}",
    )
    runlog.append_line(index, json.dumps({k: record.get(k) for k in INDEX_KEYS} | {"run_dir": rel(run_dir, runs_dir)}))
    print(f"{model} {net_id} {run_dir.name}: {outcome}, {reply.wall_s}s, usage {reply.usage}, cost ${record['cost_usd']}")
    return record


INDEX_KEYS = [
    "start", "end", "model_requested", "model_returned", "network_id", "outcome", "stop_reason",
    "message_id", "request_id", "prompt_sha256", "wall_s", "cost_usd", "code_commit",
]


def rel(path, base):
    return Path(path).relative_to(base).as_posix()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="a model ID, or 'all'")
    ap.add_argument("--network", default=None, help="a network ID, or 'all'")
    ap.add_argument("--runs", default=str(EXP / "runs"), help="where run folders are written")
    ap.add_argument("--check", action="store_true", help="check the prompts and exit")
    ap.add_argument("--count-tokens", action="store_true", help="count prompt tokens and exit")
    ap.add_argument("--replay", action="store_true", help="use Astra's recorded answers instead of the API")
    ap.add_argument("--repeat", action="store_true", help="allow another run where a run folder already exists")
    args = ap.parse_args()

    prompts = load_prompts()
    system = system_line()

    if args.check:
        for net_id, text in prompts.items():
            print(f"{net_id}: {len(text):,} chars, sha256 {runlog.sha256_text(text)[:16]}")
        print(f"system: {system!r}")
        print("prompts match the original loop.log")
        return

    if args.count_tokens:
        client = model_client.AnthropicClient()
        counts = {}
        for model in MODELS:
            counts[model] = {}
            for net_id, text in prompts.items():
                n = client.count_tokens(model, system, [{"role": "user", "content": text}])
                counts[model][net_id] = n
                price_in = model_client.PRICES[model][0]
                print(f"{model} {net_id}: {n:,} input tokens, input cost ${n * price_in / 1e6:.2f}")
        out = EXP / "eval" / "token_counts.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        runlog.write_json(out, {"counted": runlog.now(), "sdk_version": client.sdk_version, "input_tokens": counts})
        print(f"written to {out}")
        return

    if args.replay:
        if Path(args.runs).resolve() == (EXP / "runs").resolve():
            raise SystemExit("--replay must write to another folder: pass --runs DIR")
        for folder in sorted((ORIGINAL / "runs").glob("*/answer.md")):
            prompt = read_lf(folder.parent / "prompt.txt")
            net_id = next(i for i, t in prompts.items() if t == prompt)
            client = model_client.ReplayClient(read_lf(folder))
            run_one(client, "replay-astra", net_id, prompt, system, args.runs)
        return

    if not args.model or not args.network:
        ap.error("give --model and --network (or one of --check, --count-tokens, --replay)")
    models = MODELS if args.model == "all" else [args.model]
    networks = sorted(prompts) if args.network == "all" else [args.network]
    for model in models:
        if model not in MODELS:
            raise SystemExit(f"unknown model {model}; expected one of {MODELS}")
    for net_id in networks:
        if net_id not in prompts:
            raise SystemExit(f"unknown network {net_id}; expected one of {sorted(prompts)}")

    client = model_client.AnthropicClient()
    for model in models:
        for net_id in networks:
            if (Path(args.runs) / model / net_id / "run1").exists() and not args.repeat:
                print(f"{model} {net_id}: a run folder exists; skipped (use --repeat for another run)")
                continue
            run_one(client, model, net_id, prompts[net_id], system, args.runs)


if __name__ == "__main__":
    main()
