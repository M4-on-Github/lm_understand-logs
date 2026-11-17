# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a data release, not an application. It holds the complete logs behind the blog post *Sparks of Weight-Space
Programming* (see "The blog post" below): every prompt sent to the model, every reply
(with reasoning summaries), every sandboxed code run, the evaluations behind each number in the post, and the
networks the model read or wrote. There is nothing to build, lint or test. The few scripts here are kept "as run":
many hold path placeholders such as `<data>` and `<venvs>`, or import modules that are not in the repo, so most will
not run unmodified.

**Repo layout:** the original release (all `expN_*` folders, `harness/`, `LICENSE` and `README.md`) lives in
`rikiya's_exps/`. Every path in this file is relative to that folder unless it says otherwise. Quote the folder
name in shells, because it contains an apostrophe. At the repo root, `reproduce_fable_opus_plan.md` is the plan
for re-running the experiments with Claude Opus 5.5 and Claude Fable 5.2; nothing in it has been built yet.

The model under study is called "Astra" in the post: OpenAI's `gpt-6-astra`. It was run through the Codex CLI with
every built-in tool switched off.

## The blog post

- **Post:** https://rikiyat.github.io/blog/weight-space-programming/, published 2026-11-02. A "Response to
  Comments" section was added on 2026-11-12. The BibTeX entry is at the end of the post.
- **Title:** the published title is *Sparks of Weight-Space Programming: LLMs can natively read & write neural
  network weights*. The repo's `README.md` uses an older wording, "can understand and write".
- **Authors:** Rikiya Takehi, Jayden Teoh, Alex Zhang and Omar Khattab (MIT CSAIL).
- **Repo links:** the post links to the original repo, `github.com/RikiyaT/lm_understand-logs`. This checkout's
  `origin` points to `github.com/M4-on-Github/lm_understand-logs`.

How the authors frame the work, which matters when describing or extending it:

- **"Weight-Space Programming"** means treating a network's weights as a program to read and write. The authors
  stress that it is "not a method", but a concept, and that the experiments are evidence of a model capability.
- **"Natively"** means the LLM itself reasons about the weights. There is no training loop, no gradient, and no
  model trained to read or write weights. Python is a reasoning aid, not an optimizer. Gradients were excluded to
  isolate the capability, not because the concept forbids them.
- **Baselines** test only each experiment's narrow claim and are not a ranking of methods:
  - The PPO baselines in Experiments 5 and 6 show how much experience training needs.
  - In Experiment 8, turning Qwen's thinking off would avoid the loops "by not using the mode that has them", but
    it would not fix the weights.
  - The authors have not compared Astra with human interpretability researchers.
- **Stated limitations:**
  - The results are very early, and context length and the harness are inefficient.
  - Weights too large for the context need tools and forward passes.
  - Experiment 7 needed access to attention patterns.
  - The Gemma edits and the low-budget Qwen edits gained little or nothing: editing "could remove an obstacle that
    hid an ability, but it could not add an ability the model lacked".
  - Experiment 2's outline drawings show that Astra does not read weights perfectly.

Released outside this repo:

- **Edited model:** the Experiment 8 p50c model is at https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming.
  It is the base at revision `2fc06364…` with only `layers.15` and `layers.19` `mlp.down_proj.weight` changed. Its
  model card gives the vLLM settings and reports an independent re-run: 51.0% on MATH-500, against the post's 48.1%.
- **Demo:** a third party rebuilt the model from these logs and published a demo at
  https://huggingface.co/spaces/akhaliq/weight-space-programming-demo.
- **Benchmark and harness:** the authors say they are building a benchmark and harness for Weight-Space
  Programming. Neither is released.

## Where to look first

- `README.md` (top level): the experiment table, how the model was run, the meaning of each file name, the path
  placeholders, and what was left out.
- `expN_*/README.md`: each experiment's README is the authority on that folder. It maps each post tab or table row
  to a run folder, and each number in the post to a file and JSON field. Read it before making any claim about a
  result.
- `exp8_math/gemma_followup/README.md`: the follow-up to Experiment 8, which has its own README.

## Layout conventions shared across experiments

- `runs/<run>/`: one conversation, or one single-reply run.
  - Single-reply experiments (1, 2, 4, 5) keep `prompt.txt`, `answer.md`, `events.jsonl` and `run.json` at the run
    level, or under `reply/` in Experiments 4 and 5.
  - Multi-turn experiments (3, 6, 7, 8) use `turns/tNNN/{prompt.txt,answer.md,events.jsonl,run.json,stderr.log}`.
    The run level also holds `tool_calls.jsonl` (one sandbox run per line: `code`, `out`, and `s` for seconds),
    `state.json`, `final_answer.md` and the harness logs.
- `run.json` → `audit.tool_free` records the per-turn check that the model made no Codex tool call.
  `audit.usage` holds the token counts. In multi-turn runs, Codex's token usage accumulates over a conversation, so
  do not sum it across turns.
- `events.jsonl` holds the raw Codex event stream. Each run has one `"type":"error"` item, "Code Mode is
  unavailable…". It is a Codex CLI start-up notice, not a model error.
- `eval/`: the scoring, with the answer keys and ground truth. `networks/`: the weights the model saw or wrote
  (`.npz`/`.npy`, plus the exact text renderings shown to the model in Experiments 1 and 2).
- Placeholders such as `<data>`, `<repo>`, `<codex>`, `<codex_home>`, `<venvs>`, `<home>` and `<remote>` stand in
  for internal paths. Codex thread IDs are anonymized as `id-` plus 8 hex digits, and they stay consistent across
  files. Do not "fix" either.
- `fail*`, `turns_discarded/` and `refused/` keep failed or discarded harness attempts on purpose. Each
  experiment's README explains its own.

## Harness

- `harness/codex_config.toml`: the Codex config with every tool turned off. Each call overrode `model` and the
  reasoning effort.
- `harness/instructions.md`: the one-line system instructions.
- `harness/sandbox.py`: the bubblewrap Python sandbox from Experiment 6. It has no network and a per-run time
  limit, and its prelude defines `load`, `save`, `inp` and `mv` over `/work/net/*.npy`. Experiments 3, 7 and 8 used
  their own sandboxes and preludes. Their rules are stated in each experiment's prompt (`message.txt`,
  `turns/t001/prompt.txt`) and README.
- The Experiment 8 harness code (its prompts, sandbox and forward-pass server) is not included.

## Commands that work from a clean checkout

```bash
# Run everything below from inside the original release folder
cd "rikiya's_exps"

# Re-check the tool-free audit across every turn (expected output: 1125 1125)
python -c "import json,glob; fs=glob.glob('**/run.json',recursive=True); print(len(fs), sum(json.load(open(f,encoding='utf-8'))['audit']['tool_free'] is True for f in fs))"

# Recompute Experiment 8's merged.json files from parts/*/scores.json.
# This OVERWRITES the merged.json files in place. On Windows, glob order changes the key order, so the files
# show as modified even though their values are identical; compare them as parsed JSON, then restore them
# with `git checkout -- exp8_math/eval`.
python exp8_math/code/merge.py exp8_math/eval [unedited p10c p25c p50c]
python exp8_math/code/merge.py exp8_math/gemma_followup/eval
```

These scripts need external downloads:

- `exp8_math/code/apply_edit.py <base model.safetensors> <run>/edit <out>` rebuilds an edited model and checks it
  bit for bit, using only numpy (`st_numpy.py`). It needs the public base weights: `Qwen/Qwen3.5-0.8B` at revision
  `2fc06364…` or `google/gemma-3-270m-it` at revision `ac82b4e8…`. Full revisions are in the Experiment 8 README.
- `exp3_language/python_dataset/rebuild_from_manifest.py <out_dir> <site-packages…>` rebuilds the Python corpus
  for Experiment 3. It needs the package versions in `packages.txt` and CPython 3.10.12, because the output depends
  on `ast.unparse`.
- Experiment 7's `code/` (`train.py`, `eval.py`, `make_release.py`, `job_pair.sh`) is the GPU pipeline that rebuilds
  the fine-tunes that were not released. Its paths are placeholders. GPU training with bf16 autocast is not
  bit-reproducible, so a rebuilt model will not match the published hashes.

## Known discrepancies, documented on purpose

Each experiment's README explains these. Do not "correct" the data to match the post:

- Experiment 3: `eval/scores.json` → `true_copy_heads` uses an induction cutoff of 0.3. The post uses 0.2
  (`eval/heads.json`).
- Experiment 8: the unedited GPQA Diamond score is 22.7 in `merged.json`. The post's figure shows an interim 24.5.
- Experiment 7: attempts 1–3 scored "1/3 correct", which is chance, because every answer was P = 0.5 with "A" as the
  tie-break. Attempt 4 has no `score.json` because it was stopped.

## Licensing

- Logs, data and networks: CC BY 4.0.
- The authors' own `*.py` and `*.sh` scripts: MIT.
- The MinAtar source quoted in Experiment 5's prompts: GPL-3.0 (`exp5_write_from_scratch/LICENSE-MinAtar`).
- Third-party benchmark content (MATH, GSM8K, IFEval, MMLU-Pro and others): keeps its own license.
- GPQA question texts were removed from the Experiment 8 generations on purpose. Do not add them back.
