up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

dev-api:
	uvicorn api.main:app --reload --port 8001

dev-bot:
	python -m bot.main

test:
	pytest tests/ -v

lint:
	black .
	isort .
	flake8 .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f cfo.db

.PHONY: up down logs build dev-api dev-bot test lint clean