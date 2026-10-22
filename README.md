# Semantiq — document change intelligence

Semantiq compares document versions by sentence meaning and returns traceable changes, explanations, and document locations. The FastAPI backend performs parsing and semantic analysis; the Next.js frontend presents the returned results.

## Run locally

Use Python 3.11 and Node.js 18.18 or later for the current Next.js 15 release.

```bash
# Terminal 1: API
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload

# Terminal 2: frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the app and [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger. The frontend API base URL is `NEXT_PUBLIC_API_URL` in `frontend/.env.local`. Set `NEXT_PUBLIC_MAX_UPLOAD_MB` to the same limit as the backend's `MAX_UPLOAD_SIZE_MB`.

## Frontend API integration

The typed request layer lives in `frontend/lib/api/client.ts`. It uses the backend's multipart upload fields (`old_file`, `new_file`) and consumes its comparison, changes, summary, history, and document parse response schemas. The backend comparison request is synchronous; the interface shows an indeterminate analysis state until it receives the real comparison ID and then loads the persisted result.

History is served by `GET /api/v1/comparisons?limit=20&offset=0`. It returns persisted metadata and summaries, newest first. The other comparison endpoints are `POST /api/v1/comparisons`, `GET /api/v1/comparisons/{comparison_id}`, `GET /api/v1/comparisons/{comparison_id}/changes`, and `GET /api/v1/comparisons/{comparison_id}/summary`.

## Checks

```bash
cd backend
python -m compileall app
pytest

cd ../frontend
npm run lint
npm run build
```
