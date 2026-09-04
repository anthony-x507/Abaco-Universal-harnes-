"""Host-side microphone capture when the webview has no getUserMedia.

The Mac app is a WKWebView. Even with Info.plist microphone strings, the
browser surface often has no ``mediaDevices``. Chat then records through
this module (AVFoundation on Darwin, otherwise ffmpeg / sox / arecord).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


class HostAudioError(Exception):
    """The host could not start or finish a recording."""


class HostRecorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._av_recorder: object | None = None
        self._path: Path | None = None

    def start(self) -> None:
        with self._lock:
            if self._proc is not None or self._av_recorder is not None:
                raise HostAudioError("Recording is already in progress.")
            dest = Path(tempfile.mkdtemp(prefix="universal-rec-")) / "clip.wav"
            dest.parent.mkdir(parents=True, exist_ok=True)
            self._path = dest
            if sys.platform == "darwin" and self._start_avfoundation(dest):
                return
            command = self._command(dest)
            if not command:
                self._path = None
                try:
                    dest.parent.rmdir()
                except OSError:
                    pass
                raise HostAudioError(
                    "Microphone is not available in this window, and no host recorder "
                    "was found. On a Mac, allow Microphone for Universal in System "
                    "Settings → Privacy & Security, then restart the app."
                )
            self._proc = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def stop(self) -> bytes:
        with self._lock:
            path = self._path
            proc = self._proc
            av_recorder = self._av_recorder
            self._proc = None
            self._av_recorder = None
            self._path = None
        if av_recorder is not None:
            try:
                stop = getattr(av_recorder, "stop", None)
                if callable(stop):
                    stop()
            except Exception:
                pass
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        if path is None or not path.is_file() or path.stat().st_size < 44:
            raise HostAudioError(
                "No audio was captured. Allow Microphone for Universal in "
                "System Settings → Privacy & Security, then try again."
            )
        data = path.read_bytes()
        try:
            path.unlink(missing_ok=True)
            path.parent.rmdir()
        except OSError:
            pass
        return data

    def recording(self) -> bool:
        return self._proc is not None or self._av_recorder is not None

    def _start_avfoundation(self, dest: Path) -> bool:
        try:
            from AVFoundation import (  # type: ignore[import-not-found]
                AVAudioRecorder,
                AVAudioSession,
                AVAudioSessionCategoryPlayAndRecord,
                AVCaptureDevice,
                AVMediaTypeAudio,
            )
            from Foundation import NSURL  # type: ignore[import-not-found]
        except Exception:
            return False
        try:
            session = AVAudioSession.sharedInstance()
            session.setCategory_error_(AVAudioSessionCategoryPlayAndRecord, None)
            session.setActive_error_(True, None)
            try:
                AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                    AVMediaTypeAudio, lambda _granted: None
                )
            except Exception:
                pass
            url = NSURL.fileURLWithPath_(str(dest))
            settings = {
                "AVFormatIDKey": 1819304813,  # kAudioFormatLinearPCM
                "AVSampleRateKey": 16000.0,
                "AVNumberOfChannelsKey": 1,
                "AVLinearPCMBitDepthKey": 16,
                "AVLinearPCMIsFloatKey": False,
                "AVLinearPCMIsBigEndianKey": False,
            }
            recorder = AVAudioRecorder.alloc().initWithURL_settings_error_(url, settings, None)
            if recorder is None:
                return False
            if not recorder.record():
                return False
            self._av_recorder = recorder
            return True
        except Exception:
            return False

    @staticmethod
    def _command(dest: Path) -> list[str] | None:
        target = str(dest)
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            if sys.platform == "darwin":
                return [ffmpeg, "-y", "-f", "avfoundation", "-i", ":0", "-ac", "1", "-ar", "16000", target]
            if sys.platform.startswith("linux"):
                return [ffmpeg, "-y", "-f", "alsa", "-i", "default", "-ac", "1", "-ar", "16000", target]
            return [ffmpeg, "-y", "-f", "dshow", "-i", "audio=default", "-ac", "1", "-ar", "16000", target]
        rec = shutil.which("rec")
        if rec:
            return [rec, "-q", "-c", "1", "-r", "16000", target]
        arecord = shutil.which("arecord")
        if arecord:
            return [arecord, "-f", "S16_LE", "-c", "1", "-r", "16000", target]
        return None


_RECORDER = HostRecorder()


def start_host_recording() -> None:
    _RECORDER.start()


def stop_host_recording() -> bytes:
    return _RECORDER.stop()


def host_recording_active() -> bool:
    return _RECORDER.recording()
