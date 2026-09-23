"""Make a video from the command line, without the website.

    uv run python -m app.cli paper.pdf --bg minecraft.mp4 --length 30
"""

import argparse
import shutil
import sys
import time

from app.config import settings
from app.pipeline import backgrounds, run, tts


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn a PDF into a brainrot video.")
    parser.add_argument("pdf", help="path to the PDF")
    parser.add_argument("--bg", default="random", help="background filename, or 'random'")
    parser.add_argument("--length", type=int, default=60, choices=[30, 60, 180])
    parser.add_argument("--voice", default=tts.DEFAULT_VOICE, choices=sorted(tts.VOICE_IDS))
    args = parser.parse_args()

    try:
        background = backgrounds.get_background(args.bg)
    except backgrounds.BackgroundError as exc:
        sys.exit(str(exc))

    work_dir = settings.jobs_dir / f"cli-{time.strftime('%Y%m%d-%H%M%S')}"
    work_dir.mkdir(parents=True)
    pdf_path = work_dir / "input.pdf"
    shutil.copy(args.pdf, pdf_path)

    last = [""]

    def report(stage: str, progress: int) -> None:
        if stage != last[0]:
            print(f"[{progress:3d}%] {stage}", flush=True)
            last[0] = stage

    result = run.generate(pdf_path, background, args.length, args.voice, report)
    print(f"\nTitle: {result['title']}\n\n{result['script']}\n")
    print(f"Video ({result['duration']:.1f}s): {result['video_path']}")


if __name__ == "__main__":
    main()
