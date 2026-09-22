import base64
from io import BytesIO

import av
import librosa
import numpy as np


SAMPLE_RATE=16000
def _check_if_video_has_audio(video_path):
    container = av.open(video_path)
    audio_streams = [stream for stream in container.streams if stream.type == "audio"]
    if not audio_streams:
        return False
    return True


def _load_audio_with_av(src, sr, offset=0.0, duration=None):
    """Decode audio to a mono float32 waveform at ``sr`` using PyAV (ffmpeg).

    ``av`` is already a hard dependency of this module and wraps ffmpeg, so it
    can read http(s) URLs and video containers (mp4/aac, ...) that libsndfile
    cannot demux. ``offset``/``duration`` are in seconds, matching
    ``librosa.load``.
    """
    resampler = av.audio.resampler.AudioResampler(format="flt", layout="mono", rate=sr)
    chunks = []
    container = av.open(src)
    try:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):  # flush
            chunks.append(resampled.to_ndarray().reshape(-1))
    finally:
        container.close()
    y = np.concatenate(chunks).astype(np.float32) if chunks else np.zeros(0, dtype=np.float32)
    start = int(round(offset * sr))
    end = None if duration is None else start + int(round(duration * sr))
    return y[start:end]


def _load_audio(src, sr, offset=0.0, duration=None):
    """Load mono audio at ``sr`` as float32.

    Tries libsndfile via ``librosa`` first (covers wav/flac/ogg and base64
    ``BytesIO``); falls back to PyAV/ffmpeg for sources libsndfile cannot read
    (http(s) URLs and video containers such as mp4/aac). librosa>=1.0 dropped
    its built-in ffmpeg fallback, so this restores that behaviour without a
    hard dependency on a package that librosa no longer installs.
    """
    try:
        return librosa.load(src, sr=sr, offset=offset, duration=duration)[0]
    except Exception:
        if hasattr(src, "seek"):
            try:
                src.seek(0)
            except Exception:
                pass
        return _load_audio_with_av(src, sr, offset=offset, duration=duration)


def process_audio_info(conversations: list[dict] | list[list[dict]], use_audio_in_video: bool):
    """
    Read and process audio info

    Support dict keys:

    type = audio
    - audio
    - audio_start
    - audio_end

    type = video
    - video
    - video_start
    - video_end
    """
    audios = []
    if isinstance(conversations[0], dict):
        conversations = [conversations]
    for conversation in conversations:
        for message in conversation:
            if not isinstance(message["content"], list):
                continue
            for ele in message["content"]:
                if ele["type"] == "audio":
                    if "audio" in ele or "audio_url" in ele:
                        path = ele.get("audio", ele.get("audio_url"))
                        audio_start = ele.get("audio_start", 0.0)
                        audio_end = ele.get("audio_end", None)
                        if isinstance(path, np.ndarray):
                            if path.ndim > 1:
                                raise ValueError("Support only mono audio")
                            audios.append(
                                path[int(SAMPLE_RATE * audio_start) : None if audio_end is None else int(SAMPLE_RATE * audio_end)]
                            )
                            continue
                        elif path.startswith("data:audio"):
                            _, base64_data = path.split("base64,", 1)
                            data = BytesIO(base64.b64decode(base64_data))
                        elif path.startswith("http://") or path.startswith("https://"):
                            data = path
                        elif path.startswith("file://"):
                            data = path[len("file://") :]
                        else:
                            data = path
                    else:
                        raise ValueError("Unknown audio {}".format(ele))
                elif use_audio_in_video and ele["type"] == "video":
                    if "video" in ele or "video_url" in ele:
                        path = ele.get("video", ele.get("video_url"))
                        audio_start = ele.get("video_start", 0.0)
                        audio_end = ele.get("video_end", None)
                        assert _check_if_video_has_audio(
                            path
                        ), "Video must has audio track when use_audio_in_video=True"
                        if path.startswith("http://") or path.startswith("https://"):
                            data = path
                        elif path.startswith("file://"):
                            data = path[len("file://") :]
                        else:
                            data = path
                    else:
                        raise ValueError("Unknown video {}".format(ele))
                else:
                    continue
                audios.append(
                    _load_audio(
                        data,
                        sr=SAMPLE_RATE,
                        offset=audio_start,
                        duration=(audio_end - audio_start) if audio_end is not None else None,
                    )
                )
    if len(audios) == 0:
        audios = None
    return audios
