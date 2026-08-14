import io
import signal
import subprocess
import sys

import pytest

from sonara_vocal_remover.errors import ProcessingFailureError, ProcessingTimeoutError
from sonara_vocal_remover.separation import demucs_engine


class DummyProc:
    def __init__(self):
        self.pid = 4321
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self._returned = False
        self.communicate_calls = []
        self.wait_calls = []
        self.kill_called = False
        self.poll_calls = 0

    def communicate(self, timeout=None):
        self.communicate_calls.append(timeout)

        if not self._returned:
            self._returned = True
            raise subprocess.TimeoutExpired(
                cmd=["python", "-m", "demucs"],
                timeout=timeout,
            )

        return ("", "")

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        return 0

    def poll(self):
        self.poll_calls += 1
        return 0

    def kill(self):
        self.kill_called = True


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-only process termination behavior",
)
def test_windows_timeout_uses_taskkill(monkeypatch, tmp_path):
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    output_dir = tmp_path / "output"

    fake_proc = DummyProc()
    captured = {}

    def fake_popen(*args, **kwargs):
        captured["kwargs"] = kwargs
        return fake_proc

    def fake_run(cmd, check=False, stdout=None, stderr=None):
        captured["taskkill"] = cmd
        captured["check"] = check
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        return 0

    monkeypatch.setattr(demucs_engine.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(demucs_engine.sys, "platform", "win32")
    monkeypatch.setattr(demucs_engine.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(demucs_engine.subprocess, "run", fake_run)

    engine = demucs_engine.DemucsSeparationEngine(timeout_seconds=1.5)
    with pytest.raises(ProcessingTimeoutError):
        engine.separate(audio, output_dir)

    assert captured["taskkill"] == ["taskkill", "/F", "/T", "/PID", "4321"]
    assert captured["check"] is False
    assert captured["kwargs"]["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP
    assert len(fake_proc.communicate_calls) == 2
    assert fake_proc.communicate_calls[0] == 1.5


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix-only process termination behavior",
)
def test_unix_timeout_uses_new_process_group(monkeypatch, tmp_path):
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    output_dir = tmp_path / "output"

    fake_proc = DummyProc()
    captured = {}

    def fake_popen(*args, **kwargs):
        captured["kwargs"] = kwargs
        return fake_proc

    def fake_killpg(pid, sig):
        captured["killpg"] = (pid, sig)

    monkeypatch.setattr(demucs_engine.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(demucs_engine.sys, "platform", "linux")
    monkeypatch.setattr(demucs_engine.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(demucs_engine.os, "killpg", fake_killpg, raising=False)

    engine = demucs_engine.DemucsSeparationEngine(timeout_seconds=1.5)
    with pytest.raises(ProcessingTimeoutError):
        engine.separate(audio, output_dir)

    assert captured["kwargs"]["start_new_session"] is True
    assert captured["killpg"] == (4321, signal.SIGKILL)
    assert len(fake_proc.communicate_calls) == 2
    assert fake_proc.communicate_calls[0] == 1.5


def test_popen_file_not_found_raises_processing_failure(monkeypatch, tmp_path):
    audio = tmp_path / "song.wav"
    output_dir = tmp_path / "output"

    monkeypatch.setattr(demucs_engine.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(demucs_engine.subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))

    engine = demucs_engine.DemucsSeparationEngine(timeout_seconds=1.5)

    with pytest.raises(ProcessingFailureError, match="Could not invoke the `demucs` module"):
        engine.separate(audio, output_dir)
