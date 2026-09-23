"""Compose the final 9:16 video with ffmpeg: background clip + narration + burned-in captions."""

import os
import random
import re
import subprocess
from pathlib import Path
from typing import Callable

from app.config import settings
from app.pipeline.backgrounds import Background

WIDTH, HEIGHT, FPS = 1080, 1920, 30


class RenderError(Exception):
    pass


def render(
    background: Background,
    audio_path: Path,
    captions_path: Path,
    audio_duration: float,
    out_path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> None:
    work_dir = out_path.parent
    cmd = ["ffmpeg", "-y", "-nostats", "-loglevel", "error", "-progress", "pipe:1"]
    cmd += _background_input(background, audio_duration)
    cmd += ["-i", str(audio_path)]
    cmd += ["-filter_complex", f"[0:v]{_video_filter(captions_path, work_dir)}[v]"]
    cmd += ["-map", "[v]", "-map", "1:a", "-t", f"{audio_duration:.3f}"]
    cmd += _encoder_args()
    cmd += ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)]

    log_path = work_dir / "ffmpeg.log"
    with log_path.open("w") as log:
        # Run from the job folder so the subtitle path needs no filtergraph escaping.
        proc = subprocess.Popen(cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=log, text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            if on_progress and line.startswith("out_time_us="):
                value = line.split("=", 1)[1].strip()
                if value.isdigit():
                    on_progress(min(1.0, int(value) / 1e6 / audio_duration))
        code = proc.wait()

    if code != 0:
        tail = log_path.read_text(errors="replace").strip().splitlines()[-5:]
        raise RenderError("ffmpeg failed: " + " | ".join(tail))


def _background_input(background: Background, duration: float) -> list[str]:
    spare = background.duration - duration - 0.5
    if spare > 0:
        # Start somewhere random so repeat videos don't all look the same.
        return ["-ss", f"{random.uniform(0, spare):.2f}", "-i", str(background.path)]
    # Clip is shorter than the narration: loop it.
    return ["-stream_loop", "-1", "-i", str(background.path)]


def _video_filter(captions_path: Path, work_dir: Path) -> str:
    subtitles = f"subtitles={captions_path.name}"
    fonts = os.path.relpath(settings.fonts_dir, work_dir)
    # Only pass fontsdir when the path is filtergraph-safe; otherwise libass uses system fonts.
    if re.fullmatch(r"[\w./-]+", fonts):
        subtitles += f":fontsdir={fonts}"
    return (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},{subtitles}"
    )


def _encoder_args() -> list[str]:
    if settings.video_encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "23", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
