"""GGF parity regressions. No models or public tunnels are used here."""
import io
import json
from pathlib import Path
import tempfile
from contextlib import contextmanager
import unittest
from unittest.mock import Mock, patch
import uuid
import wave

import app
import native_backend
import network_settings
import workspaces
from server_controls import ServerControls
from update_app import stage_archive
import zipfile


@contextmanager
def preserved_test_dir():
    # User forbids deleting files, including automatic cleanup of QA folders.
    yield tempfile.mkdtemp(prefix="ggf-zonos-qa-")


class GGFParityTests(unittest.TestCase):
    def test_blank_password_removes_previous_login(self):
        with preserved_test_dir() as tmp:
            with patch.object(network_settings, "SETTINGS_PATH", Path(tmp) / "settings.json"):
                saved = network_settings.save_settings("public", "user", "x")
                self.assertTrue(network_settings.verify_login("user", "x", saved))
                self.assertFalse(network_settings.verify_login("user", "wrong", saved))
                blank = network_settings.save_settings("public", "", "")
                self.assertEqual(blank["digest"], "")
                self.assertEqual(blank["salt"], "")
                self.assertEqual(blank["username"], "")

    def test_local_never_uses_remote_password(self):
        local, remote = Mock(), Mock()
        local.launch.return_value = (None, "http://127.0.0.1:7865", None)
        remote.launch.return_value = (None, "http://127.0.0.1:8865", "https://test.gradio.live")
        auth = Mock()
        result = network_settings.launch_access_servers(Mock(side_effect=[local, remote]),
            mode="public", preferred_port=7865, auth=auth)
        self.assertIsNone(local.launch.call_args.kwargs["auth"])
        self.assertFalse(local.launch.call_args.kwargs["share"])
        self.assertEqual(local.launch.call_args.kwargs["server_name"], "127.0.0.1")
        self.assertIs(remote.launch.call_args.kwargs["auth"], auth)
        self.assertEqual(remote.launch.call_args.kwargs["server_name"], "127.0.0.1")
        self.assertTrue(remote.launch.call_args.kwargs["share"])
        self.assertEqual(result[-1], "https://test.gradio.live")

    def test_failed_public_link_keeps_local_app(self):
        local, remote = Mock(), Mock()
        local.launch.return_value = (None, "http://127.0.0.1:7865", None)
        remote.launch.return_value = (None, "http://127.0.0.1:8865", None)
        result = network_settings.launch_access_servers(Mock(side_effect=[local, remote]),
            mode="public", preferred_port=7865)
        self.assertIsNone(result[1])
        local.close.assert_not_called()
        remote.close.assert_called_once()

    def test_occupied_port_uses_next_port(self):
        demo = Mock()
        demo.launch.side_effect = [OSError("Cannot find empty port in range:"), (None, "next", None)]
        network_settings.launch_with_port_fallback(demo, preferred_port=7865, attempts=2)
        self.assertEqual(demo.launch.call_args.kwargs["server_port"], 7866)

    def test_release_refuses_while_generating(self):
        worker = native_backend.NativeBackend()
        release = Mock()
        controls = ServerControls(lambda: [worker.lock], release)
        worker.begin()
        try:
            self.assertIn("Generation is running", controls.perform())
            release.assert_not_called()
        finally:
            worker.finish()
        self.assertIn("Models unloaded", controls.perform())
        release.assert_called_once()

    def test_stop_only_terminates_owned_process(self):
        worker = native_backend.NativeBackend()
        owned = Mock()
        owned.poll.return_value = None
        worker.process = owned
        worker.stop()
        owned.terminate.assert_called_once()
        self.assertIsNone(worker.process)
        self.assertTrue(worker.cancelled.is_set())

    def test_two_views_cannot_generate_concurrently(self):
        worker = native_backend.NativeBackend()
        worker.begin()
        try:
            with self.assertRaisesRegex(RuntimeError, "already running"):
                worker.begin()
        finally:
            worker.finish()

    def test_long_scripts_are_not_truncated(self):
        text = " ".join("Sentence number %s." % n for n in range(300))
        parts = app.split_text(text)
        self.assertGreater(len(parts), 10)
        self.assertEqual(" ".join(parts), text)

    def test_workspace_restore_keeps_upload_and_output(self):
        with preserved_test_dir() as tmp:
            root = Path(tmp)
            with patch.object(workspaces, "ROOT", root):
                token = uuid.uuid4().hex
                reference = root / "voice.wav"
                reference.write_bytes(b"reference bytes")
                saved = workspaces.persist_reference(token, reference)
                result = root / "outputs" / "unique.wav"
                result.parent.mkdir()
                result.write_bytes(b"audio")
                workspaces.patch(token, {"text": "Kept", "reference": saved, "output": str(result)})
                restored_token, state = workspaces.initialize(token)
                self.assertEqual(restored_token, token)
                self.assertEqual(state["text"], "Kept")
                self.assertTrue(Path(workspaces.own_file(token, state["reference"])).is_file())
                self.assertEqual(workspaces.own_file(token, state["output"]), str(result))
                self.assertIsNone(workspaces.own_file(token, root / "voice.wav"))
                with self.assertRaises(ValueError):
                    workspaces.folder("../outside")

    def test_create_and_settings_are_correctly_parented(self):
        config = app.build_demo().get_config_file()
        components = {item["id"]: item for item in config["components"]}
        tabs = [item["props"]["label"] for item in components.values() if item["type"] == "tabitem"]
        self.assertEqual(tabs, ["Create", "Settings"])
        tab_ids = {item["props"]["label"]: item["id"] for item in components.values() if item["type"] == "tabitem"}
        def descendants(node):
            found = {node["id"]}
            for child in node.get("children", []):
                found |= descendants(child)
            return found
        def find_node(node, node_id):
            if node["id"] == node_id:
                return node
            for child in node.get("children", []):
                result = find_node(child, node_id)
                if result:
                    return result
        create_ids = descendants(find_node(config["layout"], tab_ids["Create"]))
        settings_ids = descendants(find_node(config["layout"], tab_ids["Settings"]))
        text_id = next(item["id"] for item in components.values() if item["props"].get("label") == "What should it say?")
        access_id = next(item["id"] for item in components.values() if item["props"].get("label") == "Access mode")
        self.assertIn(text_id, create_ids)
        self.assertNotIn(text_id, settings_ids)
        self.assertIn(access_id, settings_ids)
        self.assertNotIn(access_id, create_ids)
        parameter_id = next(item["id"] for item in components.values() if item["type"] == "accordion" and item["props"].get("label") == "Parameters")
        parameter_ids = descendants(find_node(config["layout"], parameter_id))
        self.assertTrue(parameter_ids.issubset(create_ids))
        reference_id = next(item["id"] for item in components.values() if item["type"] == "audio" and item["props"].get("label") == "Clone a voice · optional reference audio")
        self.assertNotIn(reference_id, parameter_ids)
        expression_id = next(item["id"] for item in components.values() if item["props"].get("elem_id") == "ggf-expression")
        expression_ids = descendants(find_node(config["layout"], expression_id))
        self.assertTrue(components[expression_id]["props"]["open"])
        self.assertTrue(expression_ids.issubset(create_ids))
        self.assertTrue(expression_ids.isdisjoint(parameter_ids))
        for label in ("Happy", "Sad", "Angry", "Surprised", "Valence", "Arousal", "Emotion guidance · CFG"):
            control_id = next(item["id"] for item in components.values() if item["props"].get("label") == label)
            self.assertIn(control_id, expression_ids)
            self.assertNotIn(control_id, parameter_ids)
        self.assertGreaterEqual(sum(item["type"] == "slider" for item in components.values()), 21)
        labels = [item["props"].get("label") for item in components.values()]
        self.assertIn("Access mode", labels)
        self.assertIn("Password · blank means no login", labels)
        self.assertNotIn("run-phone.bat", json.dumps(config, default=str))
        restore = [item for item in config["dependencies"] if item["api_name"] == "initialize_workspace"]
        self.assertEqual(len(restore), 1)

    def test_source_update_rejects_private_network_settings(self):
        with preserved_test_dir() as tmp:
            archive = Path(tmp) / "source.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("repo/app.py", "pass")
                output.writestr("repo/network_settings.json", "secret")
            with self.assertRaisesRegex(ValueError, "Protected"):
                stage_archive(archive, Path(tmp) / "staged", ["app.py"])

    def test_parameters_reach_native_request_without_conflicting_keys(self):
        import parameters
        values = dict(parameters.DEFAULTS, topk=42, top_p=0.7, min_p=0.2, max_tokens=3072,
                      rate_bin_enabled=True, speaking_rate_bucket=4, quality_enabled=True,
                      custom_emotion=True, happy=0.5, emotion_cfg_scale=2,
                      repetition_penalty=1.5, clean_speaker_background=True)
        body = parameters.apply({"speed": 1.2, "quality_values": {"trailing_silence_s": 0.3}}, values)
        self.assertEqual(body["topk"], 42)
        self.assertEqual(body["max_tokens"], 3072)
        self.assertEqual(body["speaking_rate_bucket"], 4)
        self.assertNotIn("speed", body)
        self.assertNotIn("quality_values", body)
        self.assertEqual(body["quality_buckets"]["trailing_silence_s"], 3)
        self.assertEqual(body["emotion_sliders"]["happy"], 0.5)
        self.assertEqual(body["emotion_cfg_scale"], 2)
        self.assertEqual(body["repetition_penalty"], 1.5)
        self.assertTrue(body["clean_speaker_background"])


if __name__ == "__main__":
    unittest.main()
