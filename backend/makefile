.PHONY: help build up down restart logs test test-cov lint format clean

help:
	@echo "Доступные команды:"
	@echo "  make build        - Собрать Docker образы"
	@echo "  make up           - Запустить все сервисы"
	@echo "  make down         - Остановить все сервисы"
	@echo "  make restart      - Перезапустить сервисы"
	@echo "  make logs         - Показать логи"
	@echo "  make test         - Запустить тесты"
	@echo "  make test-cov     - Запустить тесты с покрытием"
	@echo "  make lint         - Проверить код (flake8, mypy)"
	@echo "  make format       - Отформатировать код (black)"
	@echo "  make clean        - Очистить временные файлы"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Сервис запущен на http://localhost:8000"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-celery:
	docker-compose logs -f celery_worker

test:
	pytest backend/tests/ -v

test-cov:
	pytest backend/tests/ --cov=backend.app --cov-report=html --cov-report=term
	@echo "Отчёт о покрытии: htmlcov/index.html"

test-watch:
	pytest-watch backend/tests/

lint:
	flake8 backend/app --max-line-length=120
	mypy backend/app --ignore-missing-imports

format:
	black backend/app backend/tests --line-length=100

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov

# Database commands
db-upgrade:
	docker-compose exec backend alembic upgrade head

db-downgrade:
	docker-compose exec backend alembic downgrade -1

db-revision:
	docker-compose exec backend alembic revision --autogenerate -m "$(msg)"

# Development
shell:
	docker-compose exec backend python

celery-shell:
	docker-compose exec celery_worker celery -A backend.app.celery_app shell

# Monitoring
celery-status:
	docker-compose exec celery_worker celery -A backend.app.celery_app status

celery-inspect:
	docker-compose exec celery_worker celery -A backend.app.celery_app inspect active
