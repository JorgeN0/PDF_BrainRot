"""Runtime settings, read once from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def _path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    # "auto" picks CUDA when available, otherwise CPU.
    kokoro_device: str = os.environ.get("KOKORO_DEVICE", "auto")
    kokoro_speed: float = float(os.environ.get("KOKORO_SPEED", "1.1"))
    # libx264 works everywhere; h264_nvenc uses the NVIDIA GPU.
    video_encoder: str = os.environ.get("VIDEO_ENCODER", "libx264")
    max_pdf_mb: int = int(os.environ.get("MAX_PDF_MB", "50"))

    data_dir: Path = _path("DATA_DIR", REPO_ROOT / "data")
    backgrounds_dir: Path = _path("BACKGROUNDS_DIR", REPO_ROOT / "backgrounds")
    fonts_dir: Path = BACKEND_DIR / "assets" / "fonts"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def thumbnails_dir(self) -> Path:
        return self.data_dir / "thumbnails"


settings = Settings()
