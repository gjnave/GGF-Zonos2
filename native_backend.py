"""One app-owned, loopback-only native engine shared by local and phone UIs."""
from __future__ import annotations

import atexit
import ctypes
import os
from pathlib import Path
import runpy
import shutil
import socket
import subprocess
import threading
import time

import requests

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "zonos2"


def prepare_native_web_ui():
    """Place the app's browser UI beside an extracted native engine."""
    source = ROOT / "web" / "tts_ui.html"
    if not source.is_file():
        raise RuntimeError("App web UI is missing. Restore web/tts_ui.html from the source repository.")
    destination = RUNTIME / "web" / "tts_ui.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


class NativeBackend:
    def __init__(self):
        self.lock = threading.Lock()
        self.guard = threading.RLock()
        self.process = None
        self.log = None
        self.url = ""
        self.stage = "Ready · models load when you generate"
        self.started = 0.0
        self.cancelled = threading.Event()

    def status(self):
        elapsed = f" · {time.monotonic() - self.started:.0f}s" if self.started else ""
        return self.stage + elapsed

    def begin(self):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Generation is already running. Wait or press Stop generation.")
        self.cancelled.clear()
        self.started = time.monotonic()
        self.stage = "Starting speech generation"

    def finish(self):
        self.started = 0.0
        self.lock.release()

    def stop(self, cancel=True):
        """Only terminate the executable started by this instance; never other apps."""
        with self.guard:
            if cancel:
                self.cancelled.set()
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=10)
                self.process = None
            if self.log is not None:
                self.log.close()
                self.log = None
            self.url = ""
            self.stage = "Models released · reload automatically on the next generation"

    def ensure_loaded(self):
        if self.cancelled.is_set():
            raise RuntimeError("Generation stopped.")
        if self.process is not None and self.process.poll() is None:
            return
        self.stage = "Loading Zonos models"
        env = runpy.run_path(str(ROOT / "launch-native.py"))["native_environment"]()
        cpu = os.environ.get("ZONOS2_BACKEND", "").lower() == "cpu"
        engine = RUNTIME / ("zonos2-server.exe" if cpu else "cuda/zonos2-server.exe")
        if not engine.is_file():
            raise RuntimeError("Native engine is missing. Run install.bat first.")
        for name in ("zonos2-q6_k.gguf", "dac.gguf", "spk-encoder.gguf"):
            if not (RUNTIME / "models" / name).is_file():
                raise RuntimeError(f"Missing {name}. Run install.bat first.")
        prepare_native_web_ui()
        if not cpu:
            try:
                ctypes.WinDLL("nvcuda.dll")
            except OSError as error:
                raise RuntimeError("NVIDIA driver is unavailable. Complete normal PC setup, or use CPU mode.") from error
        with self.guard:
            if self.cancelled.is_set():
                raise RuntimeError("Generation stopped.")
            # Bind-test ephemeral ports; native startup verifies its own actual bind.
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            logs = ROOT / "logs"
            logs.mkdir(exist_ok=True)
            self.log = (logs / f"native-{time.time_ns()}.log").open("ab")
            command = [str(engine), "models/zonos2-q6_k.gguf", "--dac", "models/dac.gguf",
                       "--spk", "models/spk-encoder.gguf", "--cpu" if cpu else "--gpu",
                       "--host", "127.0.0.1", "--port", str(port), "--batch", "2",
                       "--dac-threads", "1", "--max", "4096",
                       "--tts-default-voices-dir", "default_voices"]
            self.process = subprocess.Popen(command, cwd=RUNTIME, env=env,
                stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            self.url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.cancelled.is_set():
                raise RuntimeError("Generation stopped.")
            if self.process is None or self.process.poll() is not None:
                raise RuntimeError("Native engine stopped during model load. See the newest logs/native-*.log.")
            try:
                response = requests.get(self.url + "/health", timeout=1)
                if response.ok and response.json().get("status") == "ok":
                    self.stage = "Models ready"
                    return
            except (requests.RequestException, ValueError):
                pass
            time.sleep(0.25)
        self.stop(cancel=False)
        raise RuntimeError("Model startup timed out. See logs/native-*.log.")

    def request(self, route, *, session, body=None):
        if self.cancelled.is_set():
            raise RuntimeError("Generation stopped.")
        headers = {"X-TTS-Session-ID": session}
        try:
            response = requests.request("GET" if body is None else "POST", self.url + route,
                                        headers=headers, json=body, timeout=(10, 600))
            if not response.ok:
                try:
                    detail = response.json().get("error", response.text)
                except ValueError:
                    detail = response.text[:500]
                raise RuntimeError(str(detail))
            return response
        except requests.RequestException as error:
            if self.cancelled.is_set():
                raise RuntimeError("Generation stopped.") from None
            self.stop(cancel=False)
            raise RuntimeError("Native generation disconnected. Models released; retry. See logs.") from error


WORKER = NativeBackend()
atexit.register(WORKER.stop)
