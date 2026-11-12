# Testing on Apple silicon (MacBook)

Handoff for a Claude Code session started on the Mac. This file is self-contained: the repo's agent instruction files are not in git.

## Goal (TASK-11)

Compare Laguna XS 2.1 on the Mac with the RTX 3060 PC results, and see how much more usable context the Mac gives.

- Model: `laguna-xs-2.1:q4_K_M` (33B total, 3B active, ~20 GB). Source: `models/sources.json`. Licence OpenMDW-1.1.
- Expectation to test: speeds are comparable; unified memory leaves room for more context than the PC's 32k viable context (recall failed at 64k there).
- Out of scope: Laguna S 2.1 (118B) and M.1 (225B).

## PC baseline (RTX 3060 12 GB, capped at 110 W, Ollama 0.40.16)

- Speed by allocated context (small prompt, warm tok/s): 16k 54.0, 32k 52.9, 64k 50.6, 128k 41.8, 256k 19.2. CPU share of the model rises from 52% to 85%.
- Viable-context ladder (full prompts): 8k 51.9 tok/s, 16k 48.7, 32k 44.7 (viable), 64k fails recall at 36.6 tok/s.
- Raw data: `results/speed/110W/speed_runs.jsonl`, `results/viable.jsonl`, `results/suites.jsonl`.

## Rules (keep these)

- Temperature 0, fixed seed, `think:false`. Raw results in `results/*.jsonl` are append-only; fix a scorer and re-score, never edit.
- Never start `ollama serve` by hand if the Ollama app is installed; open the app or run any `ollama` command.
- Every record carries `env` (hardware id, Ollama version, digest, harness version). Mac records get hardware id `mac-<chip>-<memory>g` automatically; they have no power limit, so power and joules per token stay empty.
- Quality is keyed by model and exact quantization; speed by machine. Never compare speeds across machines as if power were equal.
- Public repo: no client data, credentials or private email. Download only from `models/sources.json`, verify SHA-256, no gated repos, never sign in for the user.
- Do not commit or push without the user's approval.

## Steps

1. `git pull`, then `python3 -c "import sys; sys.path.insert(0,'scripts'); import bench_env; print(bench_env.HW_ID, bench_env.mac_profile())"` and record chip, memory and bandwidth. Check free memory: `memory_pressure`.
2. Install Ollama (https://ollama.com/download) if missing, then `ollama pull laguna-xs-2.1:q4_K_M`. Compare the digest in `ollama list` with `results` records (`env.digest` is `0175be1e57f4` on the PC).
3. Optional tools: `go` and `pwsh` for the Go and PowerShell tasks. Tasks needing a missing tool are recorded as skipped. AutoHotkey tasks always skip on macOS.
4. Close other heavy apps, then run:
   - `python3 scripts/speed_sweep.py --label mac --models laguna-xs-2.1:q4_K_M --ctx 16384,32768,65536,131072,262144 --repeats 3`
   - `python3 scripts/viable_ctx.py --models laguna-xs-2.1:q4_K_M` (extend the ladder past 128k if the Mac keeps passing; read the script's options first)
   - `python3 scripts/suite_runner.py --suite code-languages,summarize-categorize,consulting-cases,planted-patterns --models laguna-xs-2.1:q4_K_M`
   - `python3 scripts/tool_bench.py --models laguna-xs-2.1:q4_K_M`
5. If an MLX build exists (an Ollama MLX tag, `mlx-lm` or LM Studio), run the same steps as a separate runtime/format row. Do not mix it into the GGUF rows.
6. Summarize: Mac vs PC tok/s at each allocated context, viable-context result and first failure reason, memory used (`ollama ps`), and whether quality scores match the PC.

## Known gaps

- `scripts/export_results.py` and the site assume one machine (`win-rtx3060-12g`). Mac results are collected but not yet shown on the site (TASK-11 acceptance criterion 4).
- Power is not measured on the Mac. `sudo powermetrics --samplers gpu_power` could add it later; ask the user first.
