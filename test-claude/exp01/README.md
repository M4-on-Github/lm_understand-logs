# Experiment 1 ("which game?") with Claude Opus 5.5 and Claude Fable 5.2

A re-run of `rikiya's_exps/exp1_which_game/` with Claude models in place of Astra. The plan is in
`exp01_which_game_plan.md` in this folder.

Status: Fable 5.2 is done (4 / 4 correct). Opus 5.5 has two runs on one network and is on hold. Results and
reproducibility notes are in `WRITEUP.md`.

## Layout

```
README.md
exp01_which_game_plan.md   the plan
WRITEUP.md            results and reproducibility
requirements.txt      pinned versions of the anthropic SDK and anything else used
code/                 run_exp1.py, score_exp1.py
runs/
  index.jsonl         one line per call ever made, appended and never edited
  loop.log            one line per call started and finished
  <model>/<network id>/run1/
    prompt.txt        the text sent (LF line endings)
    instructions.md   the system line
    request.json      the full request body, minus the prompt text
    events.jsonl      the raw stream events, thinking summaries included
    answer.md         the reply text
    run.json          the run record: model, settings, API identifiers, usage, cost, the tool audit
    stderr.log        runner errors, empty when there are none
eval/
  token_counts.json   count_tokens results per model and network
  scores.json         the scorer's output
```

## How to run

From the repo root, with the virtual environment's Python (`test-claude/.venv/Scripts/python` on Windows):

```bash
python -m venv test-claude/.venv
test-claude/.venv/Scripts/python -m pip install -r test-claude/exp01/requirements.txt

# No API call:
python test-claude/exp01/code/score_exp1.py --selftest     # the scorer reproduces Astra's four original scores
python test-claude/exp01/code/run_exp1.py --check          # the prompts match the original loop.log

# Needs ANTHROPIC_API_KEY: copy .env.example to .env at the repo root and fill it in
python test-claude/exp01/code/run_exp1.py --count-tokens   # free; writes eval/token_counts.json
python test-claude/exp01/code/run_exp1.py --model claude-opus-5-5 --network a9f535cc   # one paid call
python test-claude/exp01/code/run_exp1.py --model all --network all                    # every call not yet made
python test-claude/exp01/code/score_exp1.py                # writes eval/scores.json
```

The shared modules (`model_client.py`, `runlog.py`) are in `test-claude/common/`.

## Rules

- Nothing is overwritten: a repeat run goes in `run2`, `run3`, and so on.
- Nothing is dropped: refused, cut-off and unparsed runs keep their folders.
- The API key is never written to any file here.
- Scores are computed only from the `answer.md` files and the original answer key.
