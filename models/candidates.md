# Candidate models (sizes from ollama.com tag pages, 2026-11-10)

| Model tag | Type | Disk | Ctx | Why test |
|---|---|---|---|---|
| `gpt-oss:20b` | MoE | 14 GB | 128K | Smallest MoE; needs little expert offload on 12 GB |
| `gemma4:26b-a4b-it-qat` | MoE (4B active) | 16 GB | 256K | Sliding-window attention -> cheap long context; vision |
| `nemotron-3.5-lightning:30b-a3b` | MoE (3B active) | 19-25 GB | 1M | Hybrid, 1M ctx claim; agent-oriented |
| `qwen3.6:35b-a3b-q4_K_M` | MoE (3B active) | 24 GB | 256K | Most-cited 12 GB MoE in reviews |
| `laguna-xs-2.1:q4_K_M` | MoE (3B active) | 20 GB | 256K | Agentic coding focus |
| `gemma4:12b-it-qat` | Dense | 7.2 GB | 256K | Dense baseline with vision, fits fully in VRAM |
| `gemma4:12b-it-q4_K_M` | Dense | 8.0 GB | 256K | Quant ladder: 4-bit |
| `gemma4:12b-it-q8_0` | Dense | 13 GB | 256K | Quant ladder: 8-bit; exceeds 12 GB VRAM, expect partial CPU offload |

Gemma 4 12B ladder note: ollama.com lists only qat, q4_K_M and q8_0 for 12B (no q5/q6). The mlx/mxfp8/nvfp4 tags are for Apple MLX, skipped.

Total if all pulled: ~100-110 GB. Verify free space on the drive holding the Ollama models folder.

## Uncensored A/B pairs (community builds, unvetted third-party weights)
| Uncensored tag | Base to pair against | Notes |
|---|---|---|
| `eriktonon/gemma4-uncensored` (12B) | `gemma4:12b-it-q4_K_M` | Cleanest pair; check its quant matches |
| `eriktonon/gemma4-uncensored` (26B-A4B) | `gemma4:26b-a4b-it-qat` | MoE pair |
| `eriktonon/qwen3.6-moe-uncensored` (IQ3_XS 13.5 GB) | `qwen3.6:35b-a3b-q4_K_M` | Different quant, so confounded |

Hypothesis "uncensored = more responsive" splits into: (a) speed (expect no change: same architecture),
(b) refusal rate on a benign-but-borderline prompt set (expect fewer refusals),
(c) quality (abliteration often lowers it slightly). Run T1-T7 plus a refusal set on both sides of each pair.

## Non-Ollama needs
- **Image generation:** Ollama does not generate images. Needs a separate stack (ComfyUI or stable-diffusion.cpp
  with SDXL/Flux GGUF). Decide model after text suite is done.
- **Video summary:** needs frame extraction (ffmpeg) + a vision model (gemma4) + audio transcript (whisper.cpp).
  Check ffmpeg is installed before the run.

## Caveat
Review-site tok/s figures are self-reported. Ollama has no per-expert offload flag, so results may be worse than
llama.cpp `--n-cpu-moe` numbers. Test Ollama first; add llama.cpp only if Ollama is too slow.
