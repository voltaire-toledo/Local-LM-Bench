# KV cache estimates (f16 cache), 2026-11-10

Source: Ollama /api/show model_info (layers, KV heads, key length, sliding window). Formula per attention layer:
bytes/token = 2 (K and V) x kv_heads x key_length x 2 bytes. Sliding-window layers are capped at the window size.
Hybrid models (Qwen 3.5/3.6, Granite 4, Nemotron) have attention in only a few layers, so their cache is small.
Estimates only; real use adds compute buffers (~1 GB). q8_0 KV is about half, q4_0 about a quarter.
Calibration: measured qwen3.5:9b total 6.0 GB at 16k vs 9.8 GB at 128k => ~34 KB/token (estimate 32 KB/token).

| Model | KB/token (global) | Fixed (window) | 32k | 64k | 128k | 256k |
|---|---|---|---|---|---|---|
| gemma4:12b | 16 | 0.67 GB | 1.2 | 1.7 | 2.8 | 5.0 |
| gemma4:26b-a4b | 20 | 0.42 GB | 1.1 | 1.8 | 3.1 | 5.8 |
| laguna-xs-2.1 (layer split assumed) | 40 | 0.06 GB | 1.4 | 2.7 | 5.4 | 10.7 |
| qwen3.6:35b-a3b | 20 | - | 0.7 | 1.3 | 2.7 | 5.4 |
| qwen3.5:9b | 32 | - | 1.1 | 2.1 | 4.3 | 8.6 |
| granite4:32b-a9b-h | 16 | - | 0.5 | 1.1 | 2.1 | 4.3 |
| nemotron-3.5-lightning | 7 | - | 0.2 | 0.5 | 0.9 | 1.9 |
| qwen3-coder:30b (full attention) | 96 | - | 3.2 | 6.4 | 12.9 | - |
