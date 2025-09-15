# SceneQuery

A full-stack app for video understanding and semantic search. Upload a video, we transcribe it with Whisper, chunk and embed the transcript, and let you search or chat over the video. Built with:

- Backend: Django 5, Django REST Framework, Channels (in-memory channel layer)
- ML: faster-whisper, sentence-transformers, NumPy
- Storage: PostgreSQL
- Frontend: Next.js 15 (App Router), React 19, Tailwind CSS, Zustand


## Monorepo structure

```
scenequery/
├─ backend/
│  ├─ server/              # Django project (ASGI+WSGI); settings, urls, asgi
│  ├─ videos/              # App: upload, process, search, chat (WebSockets)
│  ├─ manage.py
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/             # Next.js app router pages
│  ├─ src/lib/api.ts       # Calls backend REST endpoints
│  └─ package.json
└─ .env                    # Project-wide environment (not committed)
```


## Features

- Upload a video and track processing progress live via WebSockets
- Speech-to-text transcription via faster-whisper
- Chunking and embedding of transcript with sentence-transformers
- Vector search over transcript segments to find best relevant moments
- Optional chat over a single video, streaming tokens from OpenAI


## Prerequisites

- Node.js 18+ and a package manager (npm, pnpm, or yarn)
- Python 3.11+
- ffmpeg and ffprobe installed and on PATH (or set `FFMPEG_PATH` / `FFPROBE_PATH`)
- For OpenAI chat: an `OPENAI_API_KEY`
- PostgreSQL 13+ (required)


## Windows setup (PowerShell)

Follow these steps on Windows 10/11 using PowerShell. Administrator is not required unless installing system packages.

1) Install prerequisites

- Node.js: Download LTS from https://nodejs.org/en/download and install.
- Python 3.11+: Download from https://www.python.org/downloads/windows/ and enable “Add python.exe to PATH”.
- Git (optional but recommended): https://git-scm.com/download/win
- PostgreSQL 13+: https://www.postgresql.org/download/windows/
  - During setup, note the superuser (default `postgres`) and password.
  - After install, open “SQL Shell (psql)” and create the database:
  ```sql
  CREATE DATABASE scenequery;
  ```
- ffmpeg + ffprobe: Download static builds from https://www.gyan.dev/ffmpeg/builds/ or https://www.ffmpeg.org/download.html
  - Unzip to `C:\ffmpeg\` so the binaries are at `C:\ffmpeg\bin\ffmpeg.exe` and `C:\ffmpeg\bin\ffprobe.exe`.
  - Either add `C:\ffmpeg\bin` to your PATH, or set `FFMPEG_PATH` and `FFPROBE_PATH` in `.env`.

2) Create a `.env` file at the repo root

Copy and adjust the example below (see the Configuration section for full options):
```env
DJANGO_SECRET_KEY=your-dev-key
CORS_ALLOWED_ORIGINS=http://localhost:3000

PGDATABASE=scenequery
PGUSER=postgres
PGPASSWORD=your-postgres-password
PGHOST=localhost
PGPORT=5432

# Optional: OpenAI chat
# OPENAI_API_KEY=sk-...

# Optional: ffmpeg if not on PATH
FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe
FFPROBE_PATH=C:\\ffmpeg\\bin\\ffprobe.exe

# Frontend
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

3) Backend setup (PowerShell)

```powershell
# From repo root
python -m venv backend/venv
backend/venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt

# Initialize database
python backend/manage.py migrate

# Start HTTP + WebSocket dev server (Django runserver)
python backend/manage.py runserver 8000
```

4) Frontend setup (PowerShell)

```powershell
# From repo root
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000 and the backend at http://127.0.0.1:8000.

Tips:
- If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- If ffmpeg is not found, verify PATH or `FFMPEG_PATH`/`FFPROBE_PATH`.
- Ensure PostgreSQL service is running (check “Services” or `pg_ctl` from the installation directory).


## Quickstart (development)

Open two terminals.

1) Backend (Django)

```
# from repo root
python -m venv backend/venv
backend/venv/Scripts/activate  # Windows
# source backend/venv/bin/activate  # macOS/Linux

pip install -r backend/requirements.txt

# Create and migrate the DB
python backend/manage.py migrate

# Run the dev server (HTTP + WebSocket)
python backend/manage.py runserver 8000
```

2) Frontend (Next.js)

```
# from repo root
cd frontend
npm install
# or: pnpm install / yarn install

# In dev, the frontend proxies to the backend base URL you configure
npm run dev
```

Then open http://localhost:3000 and ensure the backend is reachable at http://127.0.0.1:8000 (configurable).


## Configuration

Provide environment variables in a root `.env` (already gitignored). The backend loads this with `python-dotenv` in `backend/server/settings.py`.

### Core backend settings (`backend/server/settings.py`)

- `DJANGO_SECRET_KEY` (default: `dev-insecure-secret-key`)
- `ALLOWED_HOSTS` (comma-separated, default: `localhost,127.0.0.1`)
- Database (PostgreSQL by default):
  - `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`
- Media/static:
  - `MEDIA_ROOT` (default: `<backend>/.media`)
- CORS:
  - `CORS_ALLOW_ALL_ORIGINS` (default: `true`)
  - `CORS_ALLOWED_ORIGINS` (CSV; default: `http://localhost:3000`)
- Channels (WebSockets): in-memory channel layer is used; Redis is not required.

### Video processing and ML

- ffmpeg/ffprobe location (see `backend/videos/utils/ffmpeg.py`):
  - `FFMPEG_PATH`, `FFPROBE_PATH` (if not on PATH)

- Whisper transcription (see `backend/videos/utils/transcription.py`):
  - `WHISPER_MODEL` (default: `small`)
  - `WHISPER_MODEL_PATH` (use a local model directory instead of downloading)
  - `ALLOW_MODEL_DOWNLOADS` (`true`/`false`, default: `true`)
  - `WHISPER_CACHE_DIR` or global `MODEL_CACHE_DIR`
  - `WHISPER_DEVICE` (`cpu` | `cuda` | `auto`, default: `cpu`)
  - `WHISPER_COMPUTE_TYPE` (e.g., `float32`, `float16`, `int8_float16`)
  - `WHISPER_CPU_THREADS` (int, default: `0` for runtime default)
  - `WHISPER_NUM_WORKERS` (int, default: `1`)
  - Tuning:
    - `WHISPER_VAD_FILTER` (`true`/`false`, default: `true`)
    - `WHISPER_BEAM_SIZE` (int, default: `1`)
    - `WHISPER_BEST_OF` (int, default: `1`)
    - `WHISPER_CONDITION_ON_PREV` (`true`/`false`, default: `false`)
    - `WHISPER_LANGUAGE` (e.g., `en`)
    - `WHISPER_TEMPERATURE` (float, default: `0`)

- Embeddings (see `backend/videos/utils/embeddings.py`):
  - `EMBED_MODEL` (default: `sentence-transformers/all-MiniLM-L6-v2`)
  - `EMBED_MODEL_PATH` (local directory override)
  - `ALLOW_MODEL_DOWNLOADS` (`true`/`false`)
  - `EMBED_CACHE_DIR` or global `MODEL_CACHE_DIR`
  - `EMBED_DEVICE` (`cuda` or `cpu`)
  - `EMBED_BATCH_SIZE` (default: `32`)

- OpenAI for chat streaming (see `backend/videos/consumers.py`):
  - `OPENAI_API_KEY` (required for chat)
  - `OPENAI_MODEL` (default: `gpt-4o-mini`)

### Frontend

- `NEXT_PUBLIC_API_BASE` (default: `http://127.0.0.1:8000`) used in `frontend/src/lib/api.ts`

Example `.env` (minimal dev):

```
# Backend
DJANGO_SECRET_KEY=your-dev-key
CORS_ALLOWED_ORIGINS=http://localhost:3000

# PostgreSQL
PGDATABASE=scenequery
PGUSER=postgres
PGPASSWORD=postgres
PGHOST=localhost
PGPORT=5432

# Optional: OpenAI chat
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Optional: ffmpeg if not on PATH
FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe
FFPROBE_PATH=C:\\ffmpeg\\bin\\ffprobe.exe

# Frontend
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```


## Running

- Backend dev server: `python backend/manage.py runserver 8000`
- Frontend dev server: `npm run dev` in `frontend/`
- Visit the UI at http://localhost:3000

Uploads and derived files (frames, media) are saved under `MEDIA_ROOT` (default `backend/.media/`). In dev, `DEBUG=True` serves media at `/media/` via `backend/server/urls.py`.

### Run with Daphne (ASGI)

For full ASGI support (HTTP + WebSockets) using Daphne instead of Django's dev server:

```powershell
# From repo root
backend/venv/Scripts/Activate.ps1
daphne -b 127.0.0.1 -p 8000 server.asgi:application
```

Notes:
- If Windows Firewall prompts, allow access on Private networks.
- Keep `NEXT_PUBLIC_API_BASE` pointing to `http://127.0.0.1:8000` so the frontend talks to Daphne.
- Static files in production should be served by a web server or CDN; in dev `DEBUG=True` is sufficient.


## API

Base URL defaults to `http://127.0.0.1:8000`.

- `POST /api/videos/` — upload a video file (form field: `file`)
- `GET /api/videos/<id>/` — get details about a video
- `GET /api/videos/<id>/search?q=...` — semantic search in transcript; returns best match and alternatives
- `GET /media/frames/<frame>.jpg` — preview frames rendered on demand

WebSocket endpoints (see `backend/videos/routing.py` and `backend/server/asgi.py`):

- `ws://127.0.0.1:8000/ws/videos/<id>/progress/` — processing progress events
- `ws://127.0.0.1:8000/ws/videos/<id>/chat/` — chat over a single video; send `{ type: "user_message", text: "..." }`


## Development notes

- The channel layer is in-memory. Redis is not used in this project.
- PostgreSQL is the default DB. Ensure the `PG*` env vars are set and the database exists.
- Large model downloads: set `ALLOW_MODEL_DOWNLOADS=false` and point to local `WHISPER_MODEL_PATH` and `EMBED_MODEL_PATH` if you work offline.
- GPU acceleration: Set `WHISPER_DEVICE=cuda` and a compatible `WHISPER_COMPUTE_TYPE` (e.g., `float16`). Ensure GPU drivers and CUDA runtime for your environment.


## Scripts and common commands

Backend:

```
# create superuser
python backend/manage.py createsuperuser

# run tests (if/when added)
pytest  # if configured
```

Frontend:

```
npm run dev
npm run build
npm start
npm run lint
```


## Troubleshooting

- ffmpeg/ffprobe not found: install ffmpeg and ensure both `ffmpeg` and `ffprobe` are on PATH, or set `FFMPEG_PATH` / `FFPROBE_PATH`.
- OpenAI chat errors: ensure `OPENAI_API_KEY` is set and reachable from the backend process.
- WebSockets not connecting in dev: confirm the backend runs on `http://127.0.0.1:8000`, `ASGI_APPLICATION` is configured (it is), and that the browser is allowed by CORS. If using a different host/port, set `NEXT_PUBLIC_API_BASE` and `CORS_ALLOWED_ORIGINS` accordingly.
- Model downloads blocked: set `ALLOW_MODEL_DOWNLOADS=true` or provide local model paths and cache directories.


## License

Proprietary/internal by default. Add your chosen license here if publishing.
