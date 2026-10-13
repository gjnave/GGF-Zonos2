# GGF Zonos2 - pre-release source backup

This is the development source backup for the native Windows Zonos2 app being prepared by Get Going Fast. **It is not a validated member installer release.**

The browser UI supports text-to-speech, reference-audio voice cloning, two-voice blending, emotion controls, Light/Dark appearance, and streaming playback. Local inference uses official Zyphra/zonos2.cpp with the official ZONOS2 GGUF Q6_K, DAC and speaker-encoder models. The PC performs inference; a temporary HTTPS tunnel lets a phone control the same server.

## Release status

- The development CUDA runtime passed generation/content checks on RTX 4090.
- Runtime binaries and models are deliberately excluded from this source repository.
- The included `install.bat` is the earlier evaluation downloader. Until the release runtime is published, it downloads the official Vulkan archive and `run.bat` defaults to CPU when the custom CUDA binary is absent. **Do not distribute this as the tested CUDA member package.**
- A portable AVX2 CPU baseline and CUDA 86/89 targets are being built separately. Other GPU hardware is unverified.
- The native runtime repository currently has no declared project license. Redistribution clarification is pending; the model card's Apache-2.0 declaration is not assigned to the C++ code or its browser UI.
- Native runtime licensing must be clarified before making this source backup public or publishing the modified upstream UI and compiled runtime.

## Planned member install and update flow

The small member ZIP will contain one CMD installer, thin run launchers, disclaimer, about and README. The installer downloads individual application files through Codeberg (primary), GitHub (mirror), then a verified Drive fallback. Repository hosts generate their archives automatically; no manually maintained source ZIP belongs in a repository. Compiled runtime assets will be separate, versioned release downloads with pinned digests. Models are downloaded directly from their official publisher with resume and SHA256 checks.

## Development preview

### Windows environment setup

`install.bat` now bootstraps hash-verified uv 0.12.24 and creates an app-local managed 64-bit Python 3.11 environment. It installs pinned requirements through uv and runs dependency checks. `/dependencies-only` tests this phase without downloading the engine/models. The small Python launcher passes the environment's CUDA runtime/cuBLAS DLL directories and packaged FFmpeg decoder to the unchanged native C++ engine. It does not use PyTorch, change the speech engine, install a CUDA toolkit/compiler, install a driver, or rely on global Python. The user's NVIDIA/CUDA PC setup remains their responsibility.

For an already provisioned local development installation, `run.bat` selects its app-local CUDA runtime, or CPU mode if absent. `run-phone.bat` starts the server if needed, verifies a pinned Cloudflare tunnel helper and prints a temporary HTTPS link. This preview has no authentication: anyone with the link can use generation/voice upload. Close the tunnel to end phone access; close the separate model-server console to free GPU memory. Never commit temporary URLs or private reference media.

## Release handoff

Keep app models, outputs, voice references, private settings and environments outside source updates. Back up an existing member ZIP before replacing it. Verify installation into a new folder and check real generated speech, not just HTTP 200 or valid WAV headers. Preserve existing working installations. Use native CMD installer logic; no PowerShell installer or globally installed Python dependency is required for this C++ runtime.
