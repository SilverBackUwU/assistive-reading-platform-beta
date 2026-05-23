# Sarvagya

Sarvagya is an assistive reading platform that accepts images or PDFs, runs OCR across multiple providers, translates the extracted text, generates Grade 2 Braille output, and produces read-aloud audio.

The main application source lives in `sarvagya copy/`, which contains:

- `backend/` - FastAPI service for upload, OCR, translation, Braille, and TTS workflows
- `frontend/` - Vite + React UI for uploading files and reviewing results
- `docs/` - project notes and architecture references
- `training_data/` - sample and manifest data used by the project

## Features

- Upload image or PDF documents
- OCR pipeline with multiple providers
- English translation of extracted text
- Grade 2 Braille generation and BRF output
- Audio synthesis for read-aloud playback

## Prerequisites

- Python 3.11+ for the backend
- Node.js 18+ for the frontend
- API credentials for any OCR or speech providers you enable

## Backend Setup

```powershell
cd "C:\D(PERSONAL)\Sarvagya\sarvagya copy\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend reads configuration from `sarvagya copy/.env`. Keep that file local and never commit it.

## Frontend Setup

```powershell
cd "C:\D(PERSONAL)\Sarvagya\sarvagya copy\frontend"
npm install
npm run dev
```

The Vite dev server usually runs on `http://localhost:5173`.

## Environment Variables

Copy `sarvagya copy/.env.example` to `sarvagya copy/.env` and fill in the required values for your environment. Common settings include:

- `APP_NAME`
- `APP_VERSION`
- `APP_HOST`
- `APP_PORT`
- `API_V1_PREFIX`
- `CORS_ORIGINS`
- `UPLOAD_DIR`
- `OUTPUT_DIR`
- `SARVAM_API_KEY`
- `SARVAM_BASE_URL`
- `GOOGLE_VISION_LANGUAGE_HINTS`
- `AZURE_DOC_INTEL_ENDPOINT`
- `AZURE_DOC_INTEL_KEY`
- `GEMINI_API_KEY`
- `LIBLOUIS_TABLE`
- `DATABASE_URL`

## Notes

- Do not commit `.env` or other credential files.
- If you add a new provider, update the backend requirements and document the setup here.
- For API details and architecture notes, see the files under `sarvagya copy/docs/`.