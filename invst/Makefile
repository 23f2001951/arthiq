.PHONY: help test test-backend test-frontend build-frontend dev-frontend dev-backend docker-up docker-down clean

help:
	@echo "ArthIQ Monorepo Commands:"
	@echo "  make dev-backend     Start FastAPI backend with hot-reload"
	@echo "  make dev-frontend    Start Vite React dev server"
	@echo "  make build-frontend  Compile Vite React frontend for production"
	@echo "  make test-backend    Run pytest in backend/"
	@echo "  make test-all        Run backend tests and frontend build check"
	@echo "  make docker-up       Build and run frontend + backend via Docker Compose"
	@echo "  make docker-down     Stop Docker Compose containers"
	@echo "  make clean           Clean caches and build artifacts"

dev-backend:
	cd backend && uvicorn invst.api.app:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

test-backend:
	cd backend && pytest tests/ -v

test-all: test-backend build-frontend

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	cd backend && $(MAKE) clean
	rm -rf frontend/dist
