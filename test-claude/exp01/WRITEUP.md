# Experiment 1 with Claude: results and reproducibility

This is a write-up of our re-run of Experiment 1 ("which game was this network trained on?") from the post
*Sparks of Weight-Space Programming*, with Claude Fable 5.2 and Claude Opus 5.5 in place of Astra
(`gpt-6-astra`). All runs were made on 2026-11-17. The plan is in `exp01_which_game_plan.md`.

## Summary

- **Fable 5.2 named the right game for all four networks**, one run each. Astra's original result was also 4 / 4.
- **Opus 5.5 is incomplete.** Only one of the four networks was run, twice. The first run was refused by the API
  partway through the reply; the second answered correctly. The other three networks are on hold.
- **Six calls were made in total**, costing $5.60. Every call is logged, including the refused one.
- These are single runs on four items. They show the capability on these networks; they do not rank the models.

## What was run

Each call is one new conversation with one reply and no tools, as in the original.

| Setting | Value |
|---|---|
| Prompt | The released `prompt.txt` for each network, unchanged (about 115,000 characters, 79,000 Claude tokens) |
| System line | `Answer the user's request.` (the released `instructions.md`) |
| Effort | `high`, the level the authors used for Astra |
| Thinking | Adaptive, with summaries returned |
| `max_tokens` | 64,000 |
| Tools, sampling settings, fallback models | None |
| SDK | `anthropic` 2.10.0 on Python 3.13.12 |
| Code | Commit `0a47f7c`, with no uncommitted changes at run time |

## Results

### Fable 5.2

| Network | True game | `Game` line of the reply | Correct | Confidence | Astra's confidence |
|---|---|---|---|---|---|
| `a9f535cc` | Breakout | Breakout (brick-breaker with a paddle on the bottom row, a bouncing ball, and three rows of bricks at the top) | Yes | 88% | 99% |
| `dfc6cb65` | Pong | Pong — a single-player (wall/squash-style) version with a vertical paddle on the left edge and a bouncing ball | Yes | 80% | 96% |
| `bdf99279` | Pac-Man | Pac-Man (a small 8×8 maze version: pellets and ghosts) | Yes | 85% | 96% |
| `0bbcc3ea` | Freeway | Frogger (a Freeway-style road-crossing game) | Yes | 90% | 97% |

Frogger counts as Freeway under the original scoring rule. We read the four `Game` lines by hand; each agrees with
the keyword scorer, and none names a second game.

### Opus 5.5 (one network only)

| Run | Outcome | `Game` line of the reply | Correct | Confidence |
|---|---|---|---|---|
| `a9f535cc` run1 | Refused partway through | none | Scored wrong | — |
| `a9f535cc` run2 | Answered | Breakout (MinAtar-style mini Breakout) | Yes | 80% |

**The refusal.** In run1 the API ended the reply with `stop_reason: refusal`, category `reasoning_extraction`.
The reply stopped in its Observations section, 2,066 characters in, before any `Game` line. The same request
passed in run2 and passed on Fable 5.2, so the refusal is not stable. Two runs do not give a refusal rate. We did
not turn on fallback models, because they would replace the model under test, and we did not change the prompt.

### Size of each call

| Model and network | Output tokens | Of which thinking | Seconds | Cost |
|---|---|---|---|---|
| Fable 5.2, `a9f535cc` | 12,511 | 10,856 | 112 | $1.13 |
| Fable 5.2, `dfc6cb65` | 10,332 | 8,672 | 96 | $1.04 |
| Fable 5.2, `bdf99279` | 5,737 | 4,452 | 55 | $0.86 |
| Fable 5.2, `0bbcc3ea` | 14,093 | 12,422 | 128 | $1.19 |
| Opus 5.5, `a9f535cc` run1 (refused) | 19,473 | 18,524 | 177 | $0.71 |
| Opus 5.5, `a9f535cc` run2 | 17,389 | 15,928 | 140 | $0.66 |

Astra used 1,679 to 1,838 output tokens per reply (833 to 1,034 for reasoning) and took 71 to 107 seconds. The
token counts come from different tokenizers and the effort levels are not equivalent across vendors, so these
numbers describe each run; they are not a like-for-like comparison.

## Reproducibility

### What we reproduced from the original

| Piece | Status |
|---|---|
| Prompts | Sent unchanged. Each prompt's length matches the character count in the original `runs/loop.log`. |
| System line, effort level, one reply per conversation, no tools | Same as the original. |
| Scorer | Rebuilt, because the original was not released. On Astra's four answers it gives the same `guess`, `correct`, `answer_line` and `confidence` as the original `eval/scores.json`. |
| Log layout | Same file names. The original tool-free audit one-liner runs on our `runs/` folder and prints `6 6`. |

### What differs from the original

- **Model call.** The original used the Codex CLI. We call the Messages API directly.
- **Scorer rules.** The keyword list, and the rule that the first game named counts, are our choices. They were
  fixed in the plan before any run. No reply so far needed the tie-break.
- **Run folders** are named by network ID, not by game.
- **Runs per condition.** One per network for Fable 5.2, as in the original. Opus 5.5 has two runs on one network.

### How to check our numbers without calling the API

From the repo root:

```bash
python test-claude/exp01/code/score_exp1.py --selftest   # the scorer against Astra's original scores
python test-claude/exp01/code/run_exp1.py --check        # the prompts against the original loop.log
python test-claude/exp01/code/score_exp1.py              # recompute eval/scores.json from the answer.md files
```

We also checked the logs themselves. For all six runs:

- The text in `answer.md` equals the text pieces of the raw stream in `events.jsonl`, joined.
- The SHA-256 of `prompt.txt` equals `prompt_sha256` in `run.json`.
- `run.json` records the model the API reported, the message ID, the request ID, the timestamps, the SDK and
  Python versions, the usage and the cost.
- No file contains the API key.

### How to repeat the runs

Set `ANTHROPIC_API_KEY` (copy `.env.example` to `.env`), install `requirements.txt`, then follow "How to run" in
`README.md`. Fable 5.2 needs 30-day data retention on the organization. A repeat costs about $0.70 per call on
Opus 5.5 and $0.85 to $1.20 on Fable 5.2 at the token use we measured.

### What cannot be reproduced

- **The reply text.** Sampling settings cannot be fixed on these models and there is no seed. A repeat sends the
  identical request and gets a different reply. The same was true of the original Astra runs.
- **The refusal.** It occurred in one of two identical requests, so a repeat may or may not hit it.
- **The model over time.** We cannot confirm that a model ID keeps pointing to the same weights. The model ID the
  API returned and the date are in each `run.json`.
- **The full reasoning.** The API returns thinking summaries only. They are in `run.json` and `events.jsonl`.

## Limits

- **Four items, one run each.** A correct open-ended answer is hard to get by chance, so each one is evidence of
  the capability. A difference of one item between models would not be reliable.
- **Opus 5.5 has no result yet.** One network out of four, with one refusal and one correct answer, supports no
  claim about the model.
- **Confidence.** Fable 5.2 stated lower confidence than Astra on every network (80–90% against 96–99%). With one
  run each, we cannot say whether that gap is stable.
- **Prompt fit.** The prompt was written and revised for Astra (`which_open_v2` in the original `run.json`).
- **Training data.** The post and its logs went public on 2026-11-02. Fable 5.2's knowledge cutoff is June 2026.
  We have not checked Opus 5.5's cutoff.

## Open work

- Opus 5.5 on `dfc6cb65`, `bdf99279` and `0bbcc3ea`: on hold. About $2.10 if no call is refused.
- More runs per network, only where a result needs them (stage 2 in the plan).
