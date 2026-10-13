# Third-party notices and release hold

This private development backup does not claim to relicense upstream components.

## Published licenses included verbatim

- `licenses/Zyphra-ZONOS2-MIT.txt`: the actual MIT license published in https://github.com/Zyphra/ZONOS2/blob/main/LICENSE, copyright 2026 Zyphra, Inc. This is the license from the original ZONOS2 implementation repository; it is not presented as a license declaration found in the separate zonos2.cpp repository.
- `licenses/ZONOS2-GGUF-Apache-2.0.txt`: standard Apache License 2.0 text, included for the model card's declared Apache-2.0 model license at https://huggingface.co/Zyphra/ZONOS2-GGUF . No model weights are bundled.
- `licenses/ggml-MIT.txt`: the verbatim MIT license from the pinned ggml submodule.

These files preserve publisher attribution and are not substituted for the different licenses of NVIDIA, Microsoft, FFmpeg, Cloudflare or other runtime dependencies.

- ZONOS2 native code/browser UI: Zyphra/zonos2.cpp v0.5.2, commit adce4ffb97e9c9c9e85de798175cb9d8711f3a1c. No project license was found in the pinned source tree, README, or GitHub license endpoint on 2026-10-13. Redistribution clarification remains pending. Do not publish this modified upstream UI or compiled runtime as a licensed GGF release without clarification.
- GGUF model files: official Zyphra/ZONOS2-GGUF model card declares Apache-2.0. Models are not included in this source backup. This model declaration does not establish the native implementation's license.
- ggml: upstream submodule commit 3af5f5760e19a96427f5f7a93b79cbdf3d4b265b carries its own MIT license. Include its verbatim license with any eventual linked runtime distribution.
- Cloudflare tunnel helper: downloaded separately from its official release. Preserve official license notices with any redistribution.
- FFmpeg, NVIDIA CUDA redistributables, Microsoft VC++/OpenMP and vendored header-only libraries: verify and include their applicable notices for any final runtime bundle. They are not included in this private source backup.

No license is fabricated for the upstream engine. GGF-specific packaging/branding does not remove third-party obligations.
