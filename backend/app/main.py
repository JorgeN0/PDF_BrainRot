"""HTTP API for the PDF -> brainrot website."""

import shutil
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import REPO_ROOT, settings
from app.jobs import Job, jobs
from app.pipeline import backgrounds, run, script_writer, tts

LENGTHS = {30, 60, 180}

for folder in (settings.jobs_dir, settings.thumbnails_dir, settings.backgrounds_dir):
    folder.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ok, message = script_writer.check_ollama()
    print(("✓ " if ok else "⚠ ") + message)
    yield


app = FastAPI(title="PDF BrainRot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    ollama_ok, ollama_msg = script_writer.check_ollama()
    ffmpeg_ok = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    count = len(backgrounds.list_backgrounds())
    return {
        "ollama": {"ok": ollama_ok, "message": ollama_msg},
        "ffmpeg": {
            "ok": ffmpeg_ok,
            "message": "ffmpeg found" if ffmpeg_ok else "ffmpeg/ffprobe not found on PATH",
        },
        "backgrounds": {
            "ok": count > 0,
            "message": f"{count} background clip(s)"
            if count
            else f"No background clips yet. Put .mp4 files in {settings.backgrounds_dir}",
        },
    }


@app.get("/api/backgrounds")
def list_backgrounds():
    return [
        {
            "id": bg.id,
            "name": bg.name,
            "duration": round(bg.duration, 1),
            "thumbnail_url": f"/api/backgrounds/{quote(bg.id)}/thumbnail",
            "video_url": f"/media/backgrounds/{quote(bg.id)}",
        }
        for bg in backgrounds.list_backgrounds()
    ]


@app.get("/api/backgrounds/{background_id}/thumbnail")
def background_thumbnail(background_id: str):
    try:
        bg = backgrounds.get_background(background_id)
    except backgrounds.BackgroundError as exc:
        raise HTTPException(404, str(exc))
    return FileResponse(backgrounds.thumbnail_path(bg), media_type="image/jpeg")


@app.get("/api/voices")
def list_voices():
    return {"default": tts.DEFAULT_VOICE, "voices": tts.VOICES}


@app.post("/api/jobs")
def create_job(
    pdf: UploadFile = File(...),
    background_id: str = Form("random"),
    length: int = Form(60),
    voice: str = Form(tts.DEFAULT_VOICE),
):
    if length not in LENGTHS:
        raise HTTPException(400, f"length must be one of {sorted(LENGTHS)}")
    if voice not in tts.VOICE_IDS:
        raise HTTPException(400, f"Unknown voice: {voice}")
    try:
        background = backgrounds.get_background(background_id)
    except backgrounds.BackgroundError as exc:
        raise HTTPException(400, str(exc))

    limit = settings.max_pdf_mb * 1024 * 1024
    data = pdf.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"PDF is larger than {settings.max_pdf_mb} MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "That file isn't a PDF")

    job = jobs.create(
        {"filename": pdf.filename, "background": background.id, "length": length, "voice": voice}
    )
    job_dir = settings.jobs_dir / job.id
    job_dir.mkdir(parents=True)
    pdf_path = job_dir / "input.pdf"
    pdf_path.write_bytes(data)

    def work(job: Job) -> None:
        result = run.generate(
            pdf_path,
            background,
            length,
            voice,
            report=lambda stage, progress: jobs.update(job.id, stage=stage, progress=progress),
        )
        jobs.update(
            job.id,
            title=result["title"],
            script=result["script"],
            video_url=f"/media/jobs/{job.id}/output.mp4",
        )

    jobs.submit(job, work)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found (jobs are forgotten when the server restarts)")
    return job.to_dict()


app.mount("/media/backgrounds", StaticFiles(directory=settings.backgrounds_dir), name="backgrounds")
app.mount("/media/jobs", StaticFiles(directory=settings.jobs_dir), name="jobs")

# After `npm run build`, serve the frontend from the same server.
_dist = REPO_ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
