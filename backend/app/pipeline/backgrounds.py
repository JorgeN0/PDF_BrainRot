"""Background gameplay clips the user drops into backgrounds/."""

import json
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv"}


class BackgroundError(Exception):
    pass


@dataclass
class Background:
    id: str
    name: str
    path: Path
    duration: float


def list_backgrounds() -> list[Background]:
    folder = settings.backgrounds_dir
    if not folder.is_dir():
        return []
    items = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            items.append(
                Background(
                    id=path.name,
                    name=path.stem.replace("_", " ").replace("-", " ").title(),
                    path=path,
                    duration=probe_duration(path),
                )
            )
    return items


def get_background(background_id: str) -> Background:
    """Look up by id from the listing only, so a crafted id can never reach another path."""
    items = list_backgrounds()
    if not items:
        raise BackgroundError(
            f"No background videos found. Put some .mp4 clips in {settings.backgrounds_dir}"
        )
    if background_id == "random":
        return random.choice(items)
    for item in items:
        if item.id == background_id:
            return item
    raise BackgroundError(f"Unknown background: {background_id}")


def thumbnail_path(background: Background) -> Path:
    """Grab one frame at 10% of the clip, cropped to 9:16, and cache it."""
    out = settings.thumbnails_dir / f"{background.id}.jpg"
    if out.exists() and out.stat().st_mtime >= background.path.stat().st_mtime:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{background.duration * 0.1:.2f}",
            "-i", str(background.path),
            "-frames:v", "1",
            "-vf", "scale=360:640:force_original_aspect_ratio=increase,crop=360:640",
            "-q:v", "4",
            str(out),
        ],
        check=True,
    )
    return out


_duration_cache: dict[tuple[Path, float], float] = {}


def probe_duration(path: Path) -> float:
    key = (path, path.stat().st_mtime)
    if key not in _duration_cache:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True,
            text=True,
        )
        try:
            _duration_cache[key] = float(json.loads(result.stdout)["format"]["duration"])
        except (KeyError, ValueError, json.JSONDecodeError):
            _duration_cache[key] = 0.0
    return _duration_cache[key]
