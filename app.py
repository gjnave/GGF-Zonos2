"""GGF Zonos2: a purpose-built Gradio frontend over the tested native engine."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import io
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
import wave

import gradio as gr

from native_backend import ROOT, RUNTIME, WORKER
from network_settings import (read_settings, save_settings, verify_login,
                              launch_access_servers, install_upload_disconnect_handling)
from server_controls import ServerControls, add_server_controls, register_servers, ensure_running
from styles import CSS, LOAD_JS, APPEARANCE_JS
import workspaces
import parameters as speech_parameters

TITLE = "GGF Zonos2"
VOICES = ["AmericanMale", "AmericanFemale", "BritishFemale"]
EMOTIONS = ["Natural", "Happy", "Sad", "Angry", "Surprised"]
DEFAULTS = ["", "AmericanMale", None, "Off", 0.5, "Natural", 1.0, -1, 0.8, 1.0, True]
ACTIVE_MODE = "local"
ACTIVE_LOCAL_URL = ""
ACTIVE_REMOTE_URL = ""
ACTIVE_AUTH = False
CONTROLS = ServerControls(lambda: [WORKER.lock], WORKER.stop)


def split_text(text, target=240):
    """Chunk long scripts at sentence/word boundaries; never truncate the script."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Enter the words you want spoken.")
    pieces = re.split(r"(?<=[.!?])\s+|\n+", text)
    chunks = []
    current = ""
    for piece in pieces:
        for word in piece.split():
            if current and len(current) + len(word) + 1 > target:
                chunks.append(current)
                current = ""
            current = (current + " " + word).strip()
    if current:
        chunks.append(current)
    return chunks


def save_workspace(token, *values):
    if not workspaces.valid_token(token):
        return
    payload = dict(zip(workspaces.FIELDS, values))
    payload["reference"] = workspaces.persist_reference(token, payload.get("reference"))
    workspaces.patch(token, payload)


def restore_workspace(token):
    token, saved = workspaces.initialize(token)
    values = [saved.get(key, default) for key, default in zip(workspaces.FIELDS, DEFAULTS)]
    if values[1] not in VOICES:
        values[1] = DEFAULTS[1]
    if values[3] not in ["Off", *VOICES]:
        values[3] = "Off"
    if values[5] not in EMOTIONS:
        values[5] = "Natural"
    values[2] = workspaces.own_file(token, values[2])
    output = workspaces.own_file(token, saved.get("output"))
    options = speech_parameters.normalize(saved.get("parameters"))
    options["embedding_file"] = workspaces.own_file(token, options.get("embedding_file"))
    return token, *values, *[options[key] for key in speech_parameters.DEFAULTS], output, output, saved.get("result_status", "Ready · enter text and choose a voice")


def save_parameters(token, *values):
    options = speech_parameters.normalize(dict(zip(speech_parameters.DEFAULTS, values)))
    if workspaces.valid_token(token):
        options["embedding_file"] = workspaces.persist_reference(token, options["embedding_file"])
        workspaces.patch(token, {"parameters": options})


def generate_with_controls(token, *values, progress=gr.Progress()):
    options = dict(zip(speech_parameters.DEFAULTS, values[len(workspaces.FIELDS):]))
    yield from generate(token, *values[:len(workspaces.FIELDS)], parameters=options, progress=progress)


def voice_payload(token, voice, reference, blend_voice, blend_amount, embedding_file=None):
    speakers = WORKER.request("/tts/speakers", session=token).json()["speakers"]
    defaults = {item["label"]: item["id"] for item in speakers}
    if reference:
        WORKER.stage = "Encoding reference voice"
        file = Path(reference)
        uploaded = WORKER.request("/tts/speakers", session=token, body={
            "label": file.stem, "speaker_audio_name": file.name,
            "speaker_audio_base64": base64.b64encode(file.read_bytes()).decode("ascii"),
        }).json()
        primary = uploaded["id"]
    elif embedding_file:
        file = Path(embedding_file)
        uploaded = WORKER.request("/tts/speakers", session=token, body={
            "label": file.stem, "speaker_embedding_name": file.name,
            "speaker_embedding_base64": base64.b64encode(file.read_bytes()).decode("ascii"),
        }).json()
        primary = uploaded["id"]
    else:
        if voice not in defaults:
            raise ValueError("Selected voice preset is missing. Rerun the installer.")
        primary = defaults[voice]
    if blend_voice != "Off":
        if blend_voice not in defaults:
            raise ValueError("Second voice preset is missing.")
        return {"speaker_blend_embedding_id_a": primary,
                "speaker_blend_embedding_id_b": defaults[blend_voice],
                "speaker_blend_t": float(blend_amount)}
    return {"speaker_embedding_id": primary}


def generate(token, text, voice, reference, blend_voice, blend_amount, emotion, emotion_amount,
             seed, temperature, rate, accurate, parameters=None, progress=gr.Progress()):
    ensure_running()
    try:
        options = speech_parameters.normalize(parameters)
        parts = split_text(text, target=options["text_per_chunk"])
        if not workspaces.valid_token(token):
            raise ValueError("The page is still initializing. Reload and try again.")
        save_workspace(token, text, voice, reference, blend_voice, blend_amount, emotion,
                       emotion_amount, seed, temperature, rate, accurate)
        reference = workspaces.read(token).get("reference")
        options["embedding_file"] = workspaces.own_file(token, options["embedding_file"])
        workspaces.patch(token, {"parameters": options})
        WORKER.begin()
    except (ValueError, RuntimeError, OSError) as error:
        raise gr.Error(str(error)) from None
    started = time.monotonic()
    try:
        yield None, None, "Starting speech generation · loading models if needed"
        progress(0.03, desc="Loading Zonos models")
        WORKER.ensure_loaded()
        conditioning = voice_payload(token, voice, reference, blend_voice, blend_amount, options["embedding_file"])
        output_dir = ROOT / "outputs"
        output_dir.mkdir(exist_ok=True)
        destination = output_dir / ("ggf-zonos2-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8] + ".wav")
        audio_format = None
        truncated = False
        partial = destination.with_suffix(".partial.wav")
        with wave.open(str(partial), "wb") as output:
            for index, part in enumerate(parts):
                WORKER.stage = f"Generating speech · part {index + 1} of {len(parts)}"
                progress((index + 0.15) / len(parts), desc=WORKER.stage)
                body = {"text": part, "stream": False, "format": "wav", "temperature": float(temperature),
                        "accurate_mode": bool(accurate), "quality_values": {"trailing_silence_s": 0.3},
                        **conditioning}
                if int(seed) >= 0:
                    body["seed"] = int(seed) + index
                if float(rate) != 1:
                    body.update(speaking_rate_enabled=True, speed=float(rate))
                if emotion != "Natural":
                    body.update(emotion_enabled=True, emotion_sliders={emotion.lower(): float(emotion_amount)}, emotion_cfg_scale=1.5)
                speech_parameters.apply(body, options)
                response = WORKER.request("/tts/generate", session=token, body=body)
                with wave.open(io.BytesIO(response.content), "rb") as wav:
                    fmt = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate())
                    if audio_format is None:
                        output.setnchannels(fmt[0]); output.setsampwidth(fmt[1]); output.setframerate(fmt[2])
                        audio_format = fmt
                    elif fmt != audio_format:
                        raise RuntimeError("Native audio format changed between chunks.")
                    truncated |= wav.getnframes() / wav.getframerate() >= options["max_tokens"] * 512 / 44100 - 0.05
                    output.writeframes(wav.readframes(wav.getnframes()))
        if WORKER.cancelled.is_set():
            raise RuntimeError("Generation stopped.")
        partial.rename(destination)
        with wave.open(str(destination), "rb") as result:
            seconds = result.getnframes() / result.getframerate()
        summary = f"Complete · {seconds:.1f}s audio · {time.monotonic() - started:.1f}s generation · saved in outputs"
        if truncated:
            summary += ". A chunk reached the engine limit; use shorter sentences if speech is cut off."
        WORKER.stage = summary
        workspaces.patch(token, {"output": str(destination), "result_status": summary})
        progress(1, desc="Saved")
        yield str(destination), str(destination), summary
    except Exception as error:
        message = "Generation stopped. Your earlier saved files are kept." if WORKER.cancelled.is_set() else str(error)
        WORKER.stop(cancel=False)
        WORKER.stage = message
        workspaces.patch(token, {"result_status": message})
        yield None, None, message
        if not WORKER.cancelled.is_set():
            raise gr.Error(message) from None
    finally:
        WORKER.finish()


def stop_generation():
    if not WORKER.lock.locked():
        return "No generation is running."
    WORKER.stop()
    return "Generation stopped. Saved files remain in outputs."


def active_network_status():
    label = {"local": "This computer only", "lan": "Local network", "public": "Temporary public link"}[ACTIVE_MODE]
    return (f"**Running mode:** {label}  \n**Local app · no login:** {ACTIVE_LOCAL_URL or 'Starting…'}  \n"
            f"**Phone/shared address:** {ACTIVE_REMOTE_URL or 'Not active'}  \n"
            f"**Remote login:** {'Enabled' if ACTIVE_AUTH else 'Off'}")


def save_network_mode(mode, username, password):
    try:
        saved = save_settings(mode, username, password)
    except (OSError, ValueError) as error:
        return f"Not saved: {error}", gr.update()
    login = "Remote login enabled. Local access stays login-free." if saved["digest"] else "No login: anyone with the shared address can use the app and Settings."
    return f"Saved. {login} Restart the app to apply these settings. The current address stays unchanged until restart.", ""


def restart_app():
    if not WORKER.lock.acquire(blocking=False):
        return "Finish or stop generation before restarting."
    try:
        ensure_running()
        import psutil
        logs = ROOT / "logs"
        logs.mkdir(exist_ok=True)
        with (logs / "restart.log").open("a", encoding="utf-8") as log:
            subprocess.Popen([sys.executable, str(ROOT / "app.py"), "--wait-for", str(os.getpid()),
                              str(psutil.Process().create_time())], cwd=ROOT, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except Exception as error:
        return f"Restart could not start: {error}"
    finally:
        WORKER.lock.release()
    return CONTROLS.perform(shutdown=True) + " Saved access settings will apply; a new phone link may be created."


def update_and_restart():
    if not WORKER.lock.acquire(blocking=False):
        return "Finish or stop generation before updating."
    try:
        ensure_running()
        from update_app import start_restart
        start_restart()
    except Exception as error:
        return f"Update could not start: {error}"
    finally:
        WORKER.lock.release()
    return CONTROLS.perform(shutdown=True) + " The updater will reopen it."


def model_status():
    files = [RUNTIME / "models" / name for name in ("zonos2-q6_k.gguf", "dac.gguf", "spk-encoder.gguf")]
    missing = [file.name for file in files if not file.is_file()]
    if missing:
        return "Missing models: " + ", ".join(missing) + ". Run install.bat."
    loaded = WORKER.process is not None and WORKER.process.poll() is None
    return f"All three models installed · {'loaded' if loaded else 'not loaded (no model VRAM allocated)'} · {'CPU' if os.environ.get('ZONOS2_BACKEND') == 'cpu' else 'NVIDIA CUDA'}"


def activity_state():
    return WORKER.status(), gr.update(interactive=not WORKER.lock.locked())


def build_demo():
    with gr.Blocks(title=TITLE + " · Get Going Fast") as demo:
        token = gr.State("")
        logo = base64.b64encode((ROOT / "assets" / "ggf-brain-logo.png").read_bytes()).decode("ascii")
        gr.HTML('<header class="ggf-hero"><div class="ggf-hero-copy">'
                '<div class="ggf-kicker">GET GOING FAST · LOCAL AI</div><h1>GGF Zonos2</h1>'
                '<p>Give your words a voice. Create speech or clone a reference.</p>'
                '<div class="ggf-links"><a href="https://getgoingfast.pro" target="_blank" rel="noopener">GetGoingFast.pro ↗</a>'
                '<a href="https://youtube.com/@TheAIHobbyGuy" target="_blank" rel="noopener">The AI Hobby Guy ↗</a></div>'
                f'</div><img alt="GGF" src="data:image/png;base64,{logo}"></header>')
        activity = gr.Markdown("Ready · models load when you generate", elem_id="ggf-activity")
        with gr.Tabs(elem_id="ggf-tabs"):
            with gr.Tab("Create", id="create"):
                text = gr.Textbox(label="What should it say?", lines=5, placeholder="Type or paste your script…")
                with gr.Row(elem_id="ggf-voice-row"):
                    with gr.Column():
                        voice = gr.Dropdown(VOICES, value="AmericanMale", label="Voice preset")
                        gr.Markdown("Or upload a reference to clone its voice. Use voices you have permission to use.")
                    reference = gr.Audio(label="Clone a voice · optional reference audio", type="filepath", sources=["upload", "microphone"])
                with gr.Accordion("Expression", open=True, elem_id="ggf-expression", elem_classes="ggf-accordion"):
                    with gr.Row():
                        emotion = gr.Dropdown(EMOTIONS, value="Natural", label="Expression preset")
                        emotion_amount = gr.Slider(0, 2, value=1, step=0.1, label="Expression strength")
                    expression_controls = speech_parameters.build_expression_controls()
                generate_button = gr.Button("Generate speech", variant="primary", elem_id="ggf-generate")
                stop_button = gr.Button("Stop generation", variant="secondary")
                with gr.Accordion("Parameters", open=False, elem_id="ggf-parameters", elem_classes="ggf-accordion"):
                    with gr.Row():
                        seed = gr.Number(label="Seed · -1 = random", value=-1, precision=0)
                        temperature = gr.Slider(0.05, 2, value=0.8, step=0.05, label="Temperature")
                        rate = gr.Slider(0.5, 2, value=1, step=0.05, label="Speaking speed")
                    gr.Markdown("#### Voice blending")
                    with gr.Row():
                        blend_voice = gr.Dropdown(["Off", *VOICES], value="Off", label="Second voice")
                        blend_amount = gr.Slider(0, 1, value=0.5, step=0.05, label="Blend · 0 = primary, 1 = second")
                    accurate = gr.Checkbox(label="Accurate speech mode", value=True)
                    parameter_controls = speech_parameters.build_controls()
                    parameter_controls.update(expression_controls)
                output = gr.Audio(label="Your speech", type="filepath", interactive=False)
                download = gr.DownloadButton("Save audio", value=None)
                result_status = gr.Markdown("")
            with gr.Tab("Settings", id="settings"):
                with gr.Accordion("Use from your phone / network access", open=True):
                    gr.Markdown("Your PC runs the model. Your phone controls the same app. Keep the PC on.")
                    current_network = gr.Markdown(active_network_status())
                    gr.Button("Refresh current address").click(active_network_status, outputs=current_network, queue=False, api_name=False)
                    settings = read_settings()
                    network_mode = gr.Dropdown(label="Access mode", choices=[("This computer only", "local"),
                        ("Local network (LAN)", "lan"), ("Temporary public link", "public")], value=settings["mode"])
                    username = gr.Textbox(label="Username · optional; defaults to ggf with a password", value=settings["username"])
                    password = gr.Textbox(label="Password · blank means no login", type="password", value="")
                    gr.Markdown("Local access always stays login-free. Remote login applies only to the separate LAN/public address. "
                                "A blank password disables login. Public links are temporary; LAN access may need Windows Firewall permission.")
                    saved_status = gr.Markdown("")
                    gr.Button("Save network settings").click(save_network_mode, [network_mode, username, password], [saved_status, password], queue=False, api_name=False)
                    gr.Button("Restart app / apply saved settings").click(restart_app, outputs=saved_status, queue=False, api_name=False)
                add_server_controls(CONTROLS)
                with gr.Accordion("Appearance", open=False):
                    appearance = gr.Radio([("Light", "light"), ("Dark", "dark")], value="light", label="Appearance on this device")
                    appearance.change(None, appearance, js=APPEARANCE_JS, queue=False)
                with gr.Accordion("Models", open=False):
                    model_info = gr.Markdown(model_status())
                    gr.Button("Refresh model status").click(model_status, outputs=model_info, queue=False, api_name=False)
                with gr.Accordion("App updates", open=False):
                    update_status = gr.Markdown("Source updates use Codeberg first, then GitHub. Models, settings and outputs are kept.")
                    from update_app import check_update
                    gr.Button("Check for updates").click(check_update, outputs=update_status, api_name=False)
                    gr.Button("Update and restart").click(update_and_restart, outputs=update_status, queue=False, api_name=False)
        gr.Markdown("Powered by **ZONOS2** from Zyphra · native Windows CUDA inference · outputs saved locally in `outputs`.", elem_classes="ggf-powered")
        fields = [text, voice, reference, blend_voice, blend_amount, emotion, emotion_amount, seed, temperature, rate, accurate]
        option_fields = [parameter_controls[key] for key in speech_parameters.DEFAULTS]
        demo.load(restore_workspace, token, [token, *fields, *option_fields, output, download, result_status], js=LOAD_JS, api_name="initialize_workspace")
        demo.load(active_network_status, outputs=current_network, queue=False, api_name=False)
        for field in fields:
            field.input(save_workspace, [token, *fields], queue=False, api_name=False)
        for field in option_fields:
            if isinstance(field, gr.File):
                field.upload(save_parameters, [token, *option_fields], queue=False, api_name=False)
                field.clear(save_parameters, [token, *option_fields], queue=False, api_name=False)
            else:
                field.input(save_parameters, [token, *option_fields], queue=False, api_name=False)
        generate_button.click(generate_with_controls, [token, *fields, *option_fields], [output, download, result_status], concurrency_limit=8, api_name="generate_speech")
        stop_button.click(stop_generation, outputs=result_status, queue=False, api_name=False)
        gr.Timer(1).tick(activity_state, outputs=[activity, generate_button], queue=False, api_name=False)
    return demo


def theme():
    from gradio.themes.utils.fonts import Font
    return gr.themes.Base(font=[Font("Segoe UI"), Font("Arial")]).set(
        body_background_fill="#07101f", body_background_fill_dark="#07101f",
        body_text_color="#e8eef9", body_text_color_dark="#e8eef9",
        block_background_fill="#111c2f", block_background_fill_dark="#111c2f",
        block_label_text_color="#e8eef9", block_label_text_color_dark="#e8eef9",
        block_info_text_color="#cdd9ed", block_info_text_color_dark="#cdd9ed",
        block_title_background_fill="#172842", block_title_background_fill_dark="#172842",
        block_title_text_color="#e8eef9", block_title_text_color_dark="#e8eef9",
        checkbox_label_text_color="#e8eef9", checkbox_label_text_color_dark="#e8eef9",
        checkbox_label_background_fill="#192d47", checkbox_label_background_fill_dark="#192d47",
        checkbox_label_background_fill_selected="#f5b942", checkbox_label_background_fill_selected_dark="#f5b942",
        checkbox_label_text_color_selected="#091425", checkbox_label_text_color_selected_dark="#091425",
        input_background_fill="#091425", input_background_fill_dark="#091425",
        button_primary_background_fill="#f5b942", button_primary_background_fill_dark="#f5b942",
        button_primary_text_color="#091425", button_primary_text_color_dark="#091425",
        button_secondary_background_fill="#192d47", button_secondary_background_fill_dark="#192d47",
        button_secondary_text_color="#e8eef9", button_secondary_text_color_dark="#e8eef9")


def main():
    global ACTIVE_MODE, ACTIVE_LOCAL_URL, ACTIVE_REMOTE_URL, ACTIVE_AUTH
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=int(os.environ.get("GGF_ZONOS_PORT", "7865")))
    parser.add_argument("--wait-for", nargs=2)
    args = parser.parse_args()
    if args.wait_for:
        import psutil
        pid, created = int(args.wait_for[0]), float(args.wait_for[1])
        deadline = time.monotonic() + 45
        while psutil.pid_exists(pid):
            try:
                if psutil.Process(pid).create_time() != created:
                    break
            except psutil.NoSuchProcess:
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Previous app did not stop; restart cancelled.")
            time.sleep(0.25)
    install_upload_disconnect_handling()
    settings = read_settings()
    ACTIVE_MODE = settings["mode"]
    ACTIVE_AUTH = ACTIVE_MODE != "local" and bool(settings["digest"])
    auth = (lambda username, password: verify_login(username, password, settings)) if ACTIVE_AUTH else None
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "app.lock").write_text(str(os.getpid()), encoding="ascii")
    local, remote, local_url, remote_url = launch_access_servers(
        lambda: build_demo().queue(max_size=8), mode=ACTIVE_MODE, preferred_port=args.port, auth=auth,
        inbrowser=not args.no_browser, css=CSS, theme=theme(), show_error=True,
        allowed_paths=[str((ROOT / "outputs").resolve()), str((ROOT / "jobs" / "workspaces").resolve())],
        blocked_paths=[str(ROOT / "network_settings.json"), str(ROOT / "logs"), str(ROOT / ".venv"),
                       str(RUNTIME / "models"), str(ROOT / "installer-cache")],
    )
    ACTIVE_LOCAL_URL, ACTIVE_REMOTE_URL = local_url, remote_url or ""
    if ACTIVE_MODE == "lan" and ACTIVE_REMOTE_URL:
        from urllib.parse import urlsplit
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
                # UDP route selection only: no connection payload is transmitted.
                route.connect(("192.0.2.1", 80))
                address = route.getsockname()[0]
            ACTIVE_REMOTE_URL = f"http://{address}:{urlsplit(ACTIVE_REMOTE_URL).port}/"
        except OSError:
            ACTIVE_REMOTE_URL += " · use this PC's LAN IPv4 address on your phone"
    register_servers(local, remote)
    print(f"{TITLE} ready. Phone access is configured in Settings.", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        WORKER.stop()
        for server in (local, remote):
            if server:
                server.close()


if __name__ == "__main__":
    main()
