import subprocess
from pathlib import Path


def make_clip(path: Path, seconds: float = 3, size: str = "320x180") -> Path:
    """Render a tiny synthetic landscape test clip."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30",
            "-t", str(seconds), "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )
    return path
