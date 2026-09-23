import json
import subprocess

import numpy as np
import soundfile as sf

from app.pipeline import video
from app.pipeline.backgrounds import get_background
from app.pipeline.captions import Word, write_ass
from tests.helpers import make_clip


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def test_renders_vertical_video_with_captions(tmp_settings, tmp_path):
    # Background shorter than the narration, so it has to loop.
    make_clip(tmp_settings.backgrounds_dir / "bg.mp4", seconds=1.5)
    bg = get_background("bg.mp4")

    job_dir = tmp_settings.jobs_dir / "test"
    job_dir.mkdir()
    audio = job_dir / "narration.wav"
    t = np.linspace(0, 2.5, int(24000 * 2.5), endpoint=False)
    sf.write(audio, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), 24000)
    captions = job_dir / "captions.ass"
    write_ass([Word("no", 0, 0.5), Word("cap", 0.5, 1.2), Word("fr.", 1.2, 2.4)], captions)

    progress = []
    out = job_dir / "output.mp4"
    video.render(bg, audio, captions, 2.5, out, on_progress=progress.append)

    info = probe(out)
    streams = {s["codec_type"]: s for s in info["streams"]}
    assert (streams["video"]["width"], streams["video"]["height"]) == (1080, 1920)
    assert "audio" in streams
    assert abs(float(info["format"]["duration"]) - 2.5) < 0.2
    assert progress and progress[-1] <= 1.0
