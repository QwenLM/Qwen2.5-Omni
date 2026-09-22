"""Regression tests for ``process_audio_info`` audio decoding.

These cover the paths that broke once ``librosa>=1.0`` dropped its built-in
ffmpeg fallback: extracting the audio track from a video container. The module
is loaded directly from its source file so the test needs only the package's own
declared dependencies (``av``, ``librosa``, ``numpy``), not torch/torchvision.
"""

import importlib.util
from pathlib import Path

import av
import librosa
import numpy as np


_SRC = Path(__file__).resolve().parents[1] / "src" / "qwen_omni_utils" / "v2_5" / "audio_process.py"
_spec = importlib.util.spec_from_file_location("_qwen_audio_process_under_test", _SRC)
audio_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audio_process)
process_audio_info = audio_process.process_audio_info

SR = 16000


def _tone(seconds=1.0, freq=440.0):
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _write_mp4(path, wave):
    container = av.open(str(path), "w")
    stream = container.add_stream("aac", rate=SR)
    stream.layout = "mono"
    frame = av.AudioFrame.from_ndarray(wave.reshape(1, -1), format="flt", layout="mono")
    frame.sample_rate = SR
    frame.pts = 0
    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode(None):
        container.mux(packet)
    container.close()


def test_video_audio_track_is_extracted(tmp_path):
    """A local video path with use_audio_in_video=True must decode its audio track."""
    mp4 = tmp_path / "clip.mp4"
    _write_mp4(mp4, _tone())
    conversation = [{"role": "user", "content": [{"type": "video", "video": str(mp4)}]}]
    audios = process_audio_info(conversation, use_audio_in_video=True)
    assert audios is not None and len(audios) == 1
    wave = audios[0]
    assert wave.dtype == np.float32
    assert abs(len(wave) - SR) <= 2048  # ~1s at 16kHz, allowing aac priming
    spectrum = np.abs(np.fft.rfft(wave[:SR]))
    peak = np.fft.rfftfreq(len(wave[:SR]), 1 / SR)[np.argmax(spectrum)]
    assert abs(peak - 440.0) < 5.0


def test_plain_wav_matches_librosa(tmp_path):
    """Formats libsndfile can read must stay bit-identical to librosa.load."""
    import soundfile as sf

    wav = tmp_path / "tone.wav"
    sf.write(str(wav), _tone(), SR)
    conversation = [{"role": "user", "content": [{"type": "audio", "audio": str(wav)}]}]
    audios = process_audio_info(conversation, use_audio_in_video=False)
    assert np.array_equal(audios[0], librosa.load(str(wav), sr=SR)[0])
