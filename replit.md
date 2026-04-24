# AI Code Manager Studio

FastAPI app providing a ChatGPT-style interface that uses DeepSeek for code generation and pushes results to GitHub.

## Stack
- Python 3.12 / FastAPI / Uvicorn
- SQLAlchemy async + aiosqlite (SQLite at `studio.db`)
- Jinja2 templates + static JS/CSS in `static/`

## Replit Setup
- Workflow `Start application` runs `python app.py` on port 5000 (host `0.0.0.0`).
- The Replit-provisioned `DATABASE_URL` (sync postgres) is ignored; the app uses local SQLite via `sqlite+aiosqlite:///studio.db`. Set a `sqlite+aiosqlite://` or other async URL in `DATABASE_URL` to override.
- Optional secrets: `DEEPSEEK_API_KEY`, `GITHUB_TOKEN`.
- Deployment: autoscale, runs `uvicorn app:app --host=0.0.0.0 --port=5000`.

## Notes
- `handlers/__init__.py` was renamed from a malformed `init.py ` filename in the import.
- `Settings.DEBUG` added (was referenced by `database.py` but missing).
