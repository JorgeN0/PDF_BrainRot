.PHONY: setup dev backend frontend test build

setup:
	cd backend && uv sync
	cd frontend && npm install

# Run the API and the website together (Ctrl+C stops both).
dev:
	$(MAKE) -j2 backend frontend

backend:
	cd backend && uv run uvicorn app.main:app --reload --reload-dir app --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest

# Build the website so the backend serves everything at http://localhost:8000
build:
	cd frontend && npm run build
