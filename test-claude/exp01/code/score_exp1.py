"""Scorer for Experiment 1 ("which game?").

The original scorer was not released. Its rule, from the original README: the answer's Game line is mapped to
a game by keywords, and Frogger counts as Freeway. The keyword list and the tie-break (the first game named in
the Game text counts) are fixed in exp01_which_game_plan.md, section 7.

Usage:
  python score_exp1.py --selftest          check the scorer against Astra's four answers and the original scores
  python score_exp1.py                     score test-claude/exp01/runs and write eval/scores.json
  python score_exp1.py --runs DIR --out F  score another runs folder
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ORIGINAL = REPO / "rikiya's_exps" / "exp1_which_game"
EXP = Path(__file__).resolve().parents[1]

KEYWORDS = {
    "breakout": ["breakout", "brick"],
    "pong": ["pong"],
    "pacman": ["pac-man", "pacman", "pac man"],
    "freeway": ["freeway", "frogger"],
}

# Field names of the answer format, in the order the prompt asks for them.
FIELDS = ["Observations", "Reasoning", "Game", "Description", "Confidence"]
_HEADER = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?\**[ \t]*(" + "|".join(FIELDS) + r")\b[ \t]*\**[ \t]*:?[ \t]*\**[ \t]*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)


def extract_field(answer, name):
    """Text of one field: the rest of its header line, or, if that is empty, the lines up to the next field."""
    text = answer.replace("\r\n", "\n")
    headers = list(_HEADER.finditer(text))
    for i, m in enumerate(headers):
        if m.group(1).lower() != name.lower():
            continue
        rest = m.group(2).strip()
        if rest:
            return rest
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        return text[m.end():end].strip()
    return None


def clean(line):
    """Lower-case, with Markdown emphasis removed."""
    return re.sub(r"[*_`]", "", line).strip().lower()


def map_game(game_text):
    """The game whose keyword appears first in the Game text, or None."""
    if not game_text:
        return None
    text = clean(game_text)
    best = None
    for game, words in KEYWORDS.items():
        for word in words:
            m = re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), game)
    return best[1] if best else None


def games_named(game_text):
    if not game_text:
        return []
    text = clean(game_text)
    return [
        game for game, words in KEYWORDS.items()
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) for w in words)
    ]


def confidence(answer):
    text = extract_field(answer, "Confidence")
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return None
    value = float(m.group(1))
    return int(value) if value == int(value) else value


def score_answer(answer, true_game):
    game_text = extract_field(answer, "Game")
    first_line = game_text.split("\n")[0] if game_text else None
    guess = map_game(game_text)
    return {
        "guess": guess,
        "correct": guess == true_game,
        "parsed": guess is not None,
        "answer_line": clean(first_line) if first_line else None,
        "games_named": games_named(game_text),
        "confidence": confidence(answer),
    }


def read(path):
    return Path(path).read_text(encoding="utf-8")


def selftest():
    """The scorer must reproduce the original scores.json on Astra's four answers."""
    key = json.loads(read(ORIGINAL / "eval" / "answer_key.json"))
    original = {r["id"]: r for r in json.loads(read(ORIGINAL / "eval" / "scores.json"))}
    folder_of = {"breakout": "breakout", "pong": "pong", "pacman": "pacman", "freeway": "freeway"}
    ok = True
    for net_id, entry in key.items():
        answer = read(ORIGINAL / "runs" / folder_of[entry["game"]] / "answer.md")
        got = score_answer(answer, entry["game"])
        want = original[net_id]
        for k in ("guess", "correct", "answer_line", "confidence"):
            match = got[k] == want[k]
            ok = ok and match
            if not match:
                print(f"MISMATCH {net_id} {k}: got {got[k]!r}, original {want[k]!r}")
        print(f"{net_id}: guess={got['guess']} correct={got['correct']} confidence={got['confidence']}")
    print("selftest passed" if ok else "selftest FAILED")
    return ok


def score_runs(runs_dir, out_path):
    key = json.loads(read(ORIGINAL / "eval" / "answer_key.json"))
    rows = []
    for run_json in sorted(Path(runs_dir).glob("*/*/run*/run.json")):
        run = json.loads(read(run_json))
        run_dir = run_json.parent
        net_id = run["network_id"]
        answer_path = run_dir / "answer.md"
        answer = read(answer_path) if answer_path.exists() else ""
        row = {
            "id": net_id,
            "model": run["model_requested"],
            "run": run_dir.name,
            "true": key[net_id]["game"],
            "seed": key[net_id]["seed"],
            "mode": "open",
            "outcome": run["outcome"],
        }
        row.update(score_answer(answer, key[net_id]["game"]))
        if run["outcome"] == "ok" and not row["parsed"]:
            row["outcome"] = "unparsed"
        row.update({
            "reasoning_summary": run.get("thinking_summaries", []),
            "tool_free": run["audit"]["tool_free"],
            "usage": run["audit"]["usage"],
            "wall_s": run["wall_s"],
            "cost_usd": run.get("cost_usd"),
        })
        rows.append(row)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    for r in rows:
        print(f"{r['model']} {r['id']} {r['run']}: true={r['true']} guess={r['guess']} "
              f"correct={r['correct']} confidence={r['confidence']} outcome={r['outcome']}")
    print(f"{len(rows)} runs scored -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--runs", default=str(EXP / "runs"))
    ap.add_argument("--out", default=str(EXP / "eval" / "scores.json"))
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    score_runs(args.runs, args.out)


if __name__ == "__main__":
    main()
