![Zonos 2 — Text to Speech](assets/zonos2-windows.png)

# Zonos 2 (Windows)

## A Get Going Fast Application

### [Quick Setup Helper → GetGoingFast.pro/tools/zonos2-win](https://getgoingfast.pro/tools/zonos2-win/)

The ready-to-run Windows installer is available to Get Going Fast members on the tool page above. This repository contains the application source, not the member installer ZIP or model weights.

Create speech from text, clone a reference voice, blend voices and adjust expression in a simple GGF interface. The PC performs inference; a phone can control it through the same app.

## Install and run

Extract the small installer ZIP into a writable folder on your internal drive. Double-click install.bat, then run.bat. The installer downloads application source (Codeberg first, GitHub fallback), a separate hash-verified native engine release, UV-managed Windows x64 Python 3.11, dependencies and the official Q6_K, DAC and speaker-encoder models. System Python is not used. Models and environments are not included in the ZIP. Allow at least 12 GB free. Installation does not install an NVIDIA driver or CUDA toolkit; complete normal PC setup first.

The default UI is http://127.0.0.1:7865 with occupied-port fallback. Native inference is a hidden app-owned loopback process that loads only when you generate. This is not ComfyUI, WSL or PyTorch inference. Native Windows CUDA and CPU builds use an AVX2 CPU baseline. CUDA was tested on RTX 4090 only; other GPU hardware is unverified. For CPU mode, set ZONOS2_BACKEND=cpu before running.

## Use from your phone

Open Settings → Use from your phone / network access. Choose Local network (same LAN) or Temporary public link. Enter an optional username/password; blank password means no login. Save, then use Restart app / apply saved settings. Return to Settings to copy the current phone address. Your PC must stay on. Local access always remains login-free; remote authentication uses a separate Gradio address. Passwords are stored only as salted hashes. Public links change on restart and anyone with an unauthenticated link can use the app and Settings. LAN access may require Windows Firewall permission. There is no separate phone launcher.

## Create

Type or paste the words to speak. Choose a preset, or upload/record a reference voice you have permission to use. Expression sliders stay in their own open panel immediately above Generate; technical controls are in the collapsed Parameters panel. Generate creates a unique WAV in outputs. Long scripts are chunked without a total-duration cap. If a chunk reaches its selected native token limit, the result warns about possible cutoff. Stop generation releases the owned engine. Release models in Settings frees GPU memory while keeping the UI and phone link open; next generation reloads automatically. Stop server requires confirmation and requires a local-PC restart afterward.

Uploads, controls and results are kept in a browser-token workspace on disk, so reopening the same browser origin restores them. New public URLs are different origins; browser-local workspace identifiers do not automatically transfer to a new URL. Light/Dark appearance is remembered on each device.

## Updates and publication

Settings checks repository revisions and stages host-generated repository archives before copying source. Existing files are backed up; installed models, environments, private settings, outputs and native binaries are preserved. Dependency updates use UV. Ordinary UI/source updates do not rebuild the native engine release.

Application source is published as individual files on [Codeberg](https://codeberg.org/Cognibuild/GGF-Zonos2) and [GitHub](https://github.com/gjnave/GGF-Zonos2). The bootstrap tries Codeberg first and falls back to GitHub if unavailable. Native binaries are downloaded as a separately versioned GitHub release asset; they are not bundled in the small member installer ZIP. No verified Drive fallback is configured; do not claim one.

## Notices

Keep licenses/ and THIRD-PARTY-NOTICES.md with the downloaded application. Published upstream license texts are retained without assigning a model/Python license to the separate native C++ project. The installer retains the user's original about.nfo and disclaimer.md unchanged; its legacy WSL description refers to the prior bundle, not this native app.
