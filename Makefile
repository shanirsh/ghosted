.PHONY: install install-backend install-frontend test build start clean

install: install-backend install-frontend

install-backend:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install --upgrade pip
	backend/.venv/bin/pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

test:
	cd frontend && npm test
	cd backend && ../backend/.venv/bin/python -m compileall .

build:
	cd frontend && npm run build

start:
	docker compose up --build

clean:
	rm -rf frontend/build frontend/node_modules backend/.venv
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
