"""Run the full PDF -> brainrot video pipeline for one job folder."""

import json
from pathlib import Path
from typing import Callable

from app.pipeline import captions, pdf_extract, script_writer, tts, video
from app.pipeline.backgrounds import Background

# (stage label, progress percent)
Report = Callable[[str, int], None]


def generate(
    pdf_path: Path,
    background: Background,
    length_seconds: int,
    voice: str,
    report: Report,
) -> dict:
    """Write every intermediate file next to pdf_path and return the result."""
    work_dir = pdf_path.parent

    report("Reading the PDF", 5)
    text = pdf_extract.extract_text(pdf_path)

    report("Writing the script", 15)
    result = script_writer.write_script(
        text, length_seconds, on_progress=lambda label: report(label, 15)
    )
    (work_dir / "script.json").write_text(json.dumps(result, indent=2))

    report("Recording the voiceover", 45)
    audio_path = work_dir / "narration.wav"
    words, duration = tts.synthesize(result["script"], voice, audio_path)
    captions_path = work_dir / "captions.ass"
    captions.write_ass(words, captions_path)

    report("Rendering the video", 60)
    out_path = work_dir / "output.mp4"
    video.render(
        background,
        audio_path,
        captions_path,
        duration,
        out_path,
        on_progress=lambda frac: report("Rendering the video", 60 + int(frac * 39)),
    )
    return {**result, "video_path": out_path, "duration": duration}
