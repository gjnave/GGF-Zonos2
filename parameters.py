"""Restore the native Zonos UI parameters; map every supported control to inference."""
import math
import gradio as gr

# Bin labels from the pinned Q6_K model's /tts/capabilities response.
QUALITY_BINS = {
    "lufs": ["-1000–-50", "-50–-45.5", "-45.5–-41", "-41–-36.5", "-36.5–-32", "-32–-27.5", "-27.5–-23", "-23–-18.5", "-18.5–-14", "-14–-9.5", "-9.5–-5", "-5+"],
    "estimated_snr": ["-1000–0", "0–6", "6–12", "12–18", "18–24", "24–30", "30–36", "36–42", "42–48", "48–54", "54–60", "60+"],
    "max_pause": ["0–0.5", "0.5–1", "1–1.5", "1.5–2", "2–2.5", "2.5–3", "3–3.5", "3.5–4", "4–4.5", "4.5–5", "5–5.5", "5.5–6"],
    "estimated_bandlimit_hz": ["495–3433", "3433–6371", "6371–9310", "9310–12248", "12248–15186", "15186–18124", "18124–21062", "21062–24000"],
    "leading_silence_s": ["0–0.05", "0.05–0.1", "0.1–0.25", "0.25–0.5", "0.5–1", "1–2", "2–4", "4+"],
    "trailing_silence_s": ["0–0.05", "0.05–0.1", "0.1–0.25", "0.25–0.5", "0.5–1", "1–2", "2–4", "4+"],
}
DEFAULTS = {
    "topk": 106, "top_p": 0.0, "min_p": 0.18, "max_tokens": 2000,
    "text_per_chunk": 240, "fade_out_ms": 20, "repetition_window": 50,
    "repetition_penalty": 1.2, "repetition_codebooks": 8, "clean_speaker_background": False,
    "rate_bin_enabled": False, "speaking_rate_bucket": 3, "quality_enabled": False,
    "custom_emotion": False, "emotion_strength": 1.0, "emotion_cfg_scale": 1.5,
    "happy": 0.0, "sad": 0.0, "angry": 0.0, "surprised": 0.0,
    "valence": 0.0, "arousal": 0.0, "embedding_file": None,
    **{"quality_" + key: 3 if key == "trailing_silence_s" else -1 for key in QUALITY_BINS},
}
RANGES = {
    "topk": (1, 200), "top_p": (0, 1), "min_p": (0, 1), "max_tokens": (64, 4096),
    "text_per_chunk": (100, 5000), "fade_out_ms": (0, 500), "repetition_window": (0, 512),
    "repetition_penalty": (1, 3), "repetition_codebooks": (0, 9), "speaking_rate_bucket": (0, 7),
    "emotion_strength": (0, 3), "emotion_cfg_scale": (1, 3),
    **{name: (-1, 1) for name in ("happy", "sad", "angry", "surprised", "valence", "arousal")},
    **{"quality_" + key: (-1, len(bins) - 1) for key, bins in QUALITY_BINS.items()},
}


def normalize(values):
    result = dict(DEFAULTS)
    if isinstance(values, dict):
        result.update({key: value for key, value in values.items() if key in DEFAULTS})
    for key, (low, high) in RANGES.items():
        value = float(result[key])
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Parameter {key} must be between {low} and {high}.")
        result[key] = int(value) if isinstance(DEFAULTS[key], int) else value
    for key in ("clean_speaker_background", "rate_bin_enabled", "quality_enabled", "custom_emotion"):
        result[key] = bool(result[key])
    return result


def apply(body, values):
    """No cosmetic-only sliders: these exact keys are consumed by native parse_gen_req."""
    values = normalize(values)
    for key in ("topk", "top_p", "min_p", "max_tokens", "fade_out_ms", "repetition_window",
                "repetition_penalty", "repetition_codebooks", "clean_speaker_background"):
        body[key] = values[key]
    if values["rate_bin_enabled"]:
        body.pop("speed", None)
        body.update(speaking_rate_enabled=True, speaking_rate_bucket=values["speaking_rate_bucket"])
    if values["quality_enabled"]:
        body.pop("quality_values", None)
        body["quality_buckets"] = {key: values["quality_" + key] for key in QUALITY_BINS if values["quality_" + key] >= 0}
    if values["custom_emotion"]:
        body.update(emotion_enabled=True, emotion_sliders={name: values[name] for name in
                    ("happy", "sad", "angry", "surprised", "valence", "arousal")})
    if body.get("emotion_enabled"):
        body.update(emotion_strength=values["emotion_strength"], emotion_cfg_scale=values["emotion_cfg_scale"])
    return body


def build_controls():
    controls = {}
    def slider(key, label, step=1):
        low, high = RANGES[key]
        controls[key] = gr.Slider(low, high, value=DEFAULTS[key], step=step, label=label)
    gr.Markdown("#### Sampling")
    with gr.Row():
        slider("topk", "Top-K")
        slider("top_p", "Top-P · 0 = off", 0.01)
        slider("min_p", "Min-P", 0.01)
    with gr.Row():
        slider("max_tokens", "Maximum audio tokens per chunk", 1)
        slider("text_per_chunk", "Text per chunk · characters", 10)
        slider("fade_out_ms", "End fade · milliseconds", 5)
    gr.Markdown("Long scripts are split and joined, not cut off by a total text limit. Higher token/chunk sizes use more memory.")
    gr.Markdown("#### Repetition")
    with gr.Row():
        slider("repetition_window", "Repetition window")
        slider("repetition_penalty", "Repetition penalty", 0.05)
        slider("repetition_codebooks", "Repetition codebooks")
    gr.Markdown("#### Speaking-rate bins")
    controls["rate_bin_enabled"] = gr.Checkbox(label="Use model speaking-rate bin · overrides speed slider", value=False)
    controls["speaking_rate_bucket"] = gr.Dropdown([(label, index) for index, label in enumerate(
        ["0–8", "8–11", "11–14", "14–17", "17–21", "21–28", "28–40", "40+"])], value=3, label="Speaking-rate bin")
    gr.Markdown("#### Audio quality bins")
    controls["quality_enabled"] = gr.Checkbox(label="Use model quality features", value=False)
    labels = {"lufs": "Loudness · LUFS", "estimated_snr": "Signal-to-noise ratio", "max_pause": "Maximum pause · seconds",
              "estimated_bandlimit_hz": "Bandwidth · Hz", "leading_silence_s": "Leading silence · seconds", "trailing_silence_s": "Trailing silence · seconds"}
    for feature, bins in QUALITY_BINS.items():
        controls["quality_" + feature] = gr.Dropdown([("Off · model default", -1)] + [(label, index) for index, label in enumerate(bins)],
            value=DEFAULTS["quality_" + feature], label=labels[feature])
    gr.Markdown("#### Voice options")
    controls["clean_speaker_background"] = gr.Checkbox(label="Clean reference background", value=False)
    controls["embedding_file"] = gr.File(label="Import a saved voice embedding · optional .npy", file_types=[".npy"], type="filepath")
    gr.Markdown("The reference-audio upload above takes priority over an embedding. Text normalization is unavailable in this native build; no inactive normalization switch is shown.")
    return controls


def build_expression_controls():
    """User-facing expression controls are separate from technical Parameters."""
    controls = {}
    def slider(key, label):
        low, high = RANGES[key]
        controls[key] = gr.Slider(low, high, value=DEFAULTS[key], step=0.05, label=label)
    controls["custom_emotion"] = gr.Checkbox(label="Use detailed sliders · overrides Expression preset", value=False)
    for first, second in (("happy", "sad"), ("angry", "surprised"), ("valence", "arousal")):
        with gr.Row():
            slider(first, first.title())
            slider(second, second.title())
    with gr.Row():
        slider("emotion_strength", "Emotion strength · calibrated")
        slider("emotion_cfg_scale", "Emotion guidance · CFG")
    gr.Markdown("Guidance above 1 can use about twice the compute. Expression changes the voice, not your script.")
    return controls
