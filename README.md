# PDF_BrainRot

PDF to Brainrot specifically for me so i dont pay money.

Upload a PDF, pick a background clip (Minecraft parkour, Subway Surfers, whatever), and get a
vertical 9:16 short. It has an AI voiceover explaining the PDF in brainrot style and big
word-by-word captions. Everything runs locally, with no API keys and no subscriptions.

```
PDF ─► text (PyMuPDF) ─► script (Ollama, local LLM) ─► voiceover (Kokoro, local TTS)
    ─► captions (.ass) ─► ffmpeg: background cropped to 9:16 + voice + captions ─► MP4
```

## Requirements

- [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you)
- Node.js 20+
- ffmpeg (with libass, which most builds include)
- [Ollama](https://ollama.com) with a model pulled: `ollama pull qwen2.5:7b`
- An NVIDIA GPU is optional. Kokoro and Ollama both fall back to the CPU, just more slowly.

## Setup

```sh
ollama pull qwen2.5:7b
make setup           # uv sync + npm install (PyTorch is a big download the first time)
```

Put a few gameplay clips in [`backgrounds/`](backgrounds/README.md).

## Run

```sh
make dev             # API on :8000, website on http://localhost:5173
```

Or run `make backend` and `make frontend` in two terminals. The first video takes longer
because Kokoro downloads its voice model (about 330 MB) on first use.

To serve everything from one port instead, run `make build` and then `make backend`, and open
http://localhost:8000.

There's also a command-line version that skips the website:

```sh
cd backend
uv run python -m app.cli ~/Downloads/reading.pdf --bg minecraft_parkour.mp4 --length 60
```

## Settings

Set these as environment variables when starting the backend:

| Variable          | Default                  | What it does                                   |
| ----------------- | ------------------------ | ---------------------------------------------- |
| `OLLAMA_MODEL`    | `qwen2.5:7b`             | Which Ollama model writes the script           |
| `OLLAMA_URL`      | `http://localhost:11434` | Where Ollama is running                        |
| `KOKORO_DEVICE`   | `auto`                   | `cuda`, `cpu`, or `auto`                       |
| `KOKORO_SPEED`    | `1.1`                    | Speaking speed                                 |
| `VIDEO_ENCODER`   | `libx264`                | Set `h264_nvenc` for GPU encoding (faster)     |
| `MAX_PDF_MB`      | `50`                     | Upload size limit                              |
| `BACKGROUNDS_DIR` | `./backgrounds`          | Where background clips live                    |
| `DATA_DIR`        | `./data`                 | Uploads, rendered videos, and thumbnails       |

## Where things are

- `backend/app/pipeline/`: one module per step (`pdf_extract`, `script_writer`, `tts`,
  `captions`, `video`, `backgrounds`), wired together in `run.py`
- `backend/app/main.py`: the HTTP API (`/api/jobs`, `/api/backgrounds`, `/api/voices`,
  `/api/health`)
- `frontend/src/`: the React website
- `data/jobs/<id>/`: every job's files (`input.pdf`, `script.json`, `narration.wav`,
  `captions.ass`, `output.mp4`)

Run the tests with `make test`.

## Known limits

- Scanned PDFs (images only, no selectable text) aren't supported yet. There's no OCR.
- Script quality depends on the local model. Bigger models write better scripts but need more
  VRAM. Change the model with `OLLAMA_MODEL`.
- Jobs are kept in memory, so restarting the backend forgets them. Their files stay in
  `data/jobs/`.
