# Image generation tests: plan and downloads (proposal, 2026-11-11)

Not yet downloaded. Sizes marked * are estimates; the rest come from Hugging Face and GitHub listings.

## Runtime: stable-diffusion.cpp
One CLI binary, scriptable and repeatable (seed, steps, timing), no custom nodes. Supports Z-Image, FLUX.2 klein, Qwen-Image 2.1, HiDream-O1 and others. Backends include CUDA (this PC) and Metal (the Mac), so the same suite can run on both.
- `sd-master-465adf3-bin-win-cuda12-x64.zip` 367 MB and `cudart-sd-bin-win-cu12-x64.zip` 564 MB, from github.com/leejet/stable-diffusion.cpp release master-1086-465adf3 (2026-11-10). Verify the SHA-256 after download.

## Core models (both Apache-2.0, not gated)
| Model | Files | Size |
|---|---|---|
| Z-Image-Turbo (6.15B, 8 steps) | `z-image-turbo-Q8_0.gguf` (leejet/Z-Image-Turbo-GGUF or unsloth), `Qwen3-4B-Instruct-2507` GGUF text encoder (unsloth), `ae.sft` VAE (FLUX.1-schnell) | 7.2 GB + ~2.5 GB* + ~0.3 GB* |
| FLUX.2 klein 4B (4 steps, supports image editing) | `flux-2-klein-4b-Q8_0.gguf` (leejet or unsloth), `Qwen3-4B` GGUF text encoder (unsloth), `flux2_ae.safetensors` VAE | 4.3 GB + ~2.5 GB* + ~0.3 GB* |

Caution: the documented FLUX.2 VAE lives in `black-forest-labs/FLUX.2-dev`, which may be gated. If so, use the ungated Comfy-Org repack or accept the terms yourself.

## SDXL (requested)
Stability AI `stabilityai/stable-diffusion-xl-base-1.0`, ungated, OpenRAIL++-M license (commercial use allowed with use restrictions). `sd_xl_base_1.0.safetensors` is 6.94 GB; fits 12 GB VRAM with room to spare. stable-diffusion.cpp supports SDXL and SDXL-Turbo. Weaker than the newer models at rendering text, but it has the largest ecosystem, including LayerDiffuse for native transparent PNGs (needs ComfyUI or Forge, which is third-party code to vet first).

## Optional third model
Qwen-Image 2.1 (7.1B): unsloth `qwen-image-2.1-Q4_K_M.gguf` 4.2 GB plus a Qwen text encoder (size unverified). The BF16 repo carries an `rgba` tag, but nothing states what it does. License is `qwen-research` (non-commercial), so it matters for client logos.

## Tests
1. **Logo, transparent PNG** (5 briefs: wordmark, monogram, emblem, mascot, icon). Native RGBA if a model supports it, otherwise a flat background plus chroma-key cutout. Automatic fringe check by compositing on black, white and checker; human score on the rest.
2. **Logo, SVG.** Text models write the SVG from the same briefs. Checks: valid XML, viewBox, no external references, renders in Edge headless; human score on resemblance and cleanliness.
3. **LinkedIn carousel** (5 slides, 4:5 portrait, short headline text on each). Style consistency across slides, text accuracy (OCR by a local vision model, then spot-checked).
4. **Folder icon derived from a generated logo** (reference-image edit; FLUX.2 klein supports it). Fidelity to the logo and legibility when downscaled to 256, 64 and 32 px. No ICO conversion.

Record per image: seconds, steps, resolution, seed, VRAM peak, GPU watts, joules per image, binary version and model file hashes. Three seeds per brief.
