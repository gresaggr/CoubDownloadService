# Coub Download Service v2.0

Асинхронный сервис загрузки и обработки Coub видео с улучшенной безопасностью и тестированием.

## 🎯 Основные возможности

- ✅ Асинхронная загрузка видео с Coub.com
- ✅ Проверка дубликатов (кэширование загруженных файлов)
- ✅ Отображение прогресса загрузки в реальном времени
- ✅ Валидация URL и защита от path traversal
- ✅ Rate limiting (защита от злоупотреблений)
- ✅ Ограничение размера файлов
- ✅ Health check endpoints
- ✅ Улучшенный UI с анимациями
- ✅ Полное покрытие тестами

## 🛠 Технологии

### Backend
- **FastAPI** - современный асинхронный веб-фреймворк
- **Celery** - распределённая очередь задач
- **Redis** - брокер сообщений и кэш
- **PostgreSQL** - основная база данных
- **SQLAlchemy** - ORM с асинхронной поддержкой
- **Pydantic v2** - валидация данных
- **httpx** - асинхронный HTTP клиент
- **slowapi** - rate limiting

### Frontend
- **Vue.js 3** - прогрессивный JavaScript фреймворк
- Современный CSS с анимациями и transitions

### DevOps
- **Docker** & **docker-compose** - контейнеризация
- **pytest** - тестирование
- **black** - форматирование кода
- **flake8** & **mypy** - линтинг и type checking

## 📦 Установка и запуск

### Быстрый старт

1. **Клонируйте репозиторий**
```bash
git clone <repository-url>
cd coub-download-service
```

2. **Создайте .env файл**
```bash
cp example.env .env
# Отредактируйте .env по необходимости
```

3. **Запустите сервисы**
```bash
make build
make up
```

4. **Откройте в браузере**
- Frontend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Альтернативный запуск без Make

```bash
docker-compose build
docker-compose up -d
```

## 🧪 Тестирование

### Запуск всех тестов

```bash
make test
```

### Запуск с покрытием

```bash
make test-cov
# Откройте htmlcov/index.html для просмотра отчёта
```

### Запуск конкретных тестов

```bash
pytest backend/tests/test_api.py -v
pytest backend/tests/test_crud.py::TestFileRecordCRUD::test_create_file_record -v
```

### Подготовка тестовой БД

```bash
# Создайте тестовую БД
docker exec -it coub_db psql -U postgres -c "CREATE DATABASE test_filedb;"
```

## 📚 API Документация

### Основные endpoints

#### `POST /api/process`
Начать обработку Coub URL
```json
{
  "url": "https://coub.com/view/VIDEO_ID"
}
```

#### `GET /api/task/{task_id}`
Проверить статус задачи
```json
{
  "task_id": "abc-123",
  "status": "processing",
  "progress": {
    "current": 45,
    "total": 100,
    "status": "Загружено 2.3 MB..."
  }
}
```

#### `GET /api/download/{file_id}`
Скачать готовый файл

#### `GET /api/files`
Получить список всех файлов (с пагинацией)

#### `GET /health`
Health check приложения

#### `GET /health/db`
Health check базы данных

#### `GET /health/redis`
Health check Redis

## 🔧 Разработка

### Структура проекта

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI приложение
│   │   ├── celery_app.py    # Celery конфигурация
│   │   ├── config.py        # Настройки
│   │   ├── models.py        # SQLAlchemy модели
│   │   ├── schemas.py       # Pydantic схемы
│   │   ├── crud.py          # CRUD операции
│   │   ├── tasks.py         # Celery задачи
│   │   ├── database.py      # Настройка БД
│   │   ├── utils.py         # Вспомогательные функции
│   │   └── exceptions.py    # Кастомные исключения
│   ├── tests/               # Тесты
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_crud.py
│   │   ├── test_utils.py
│   │   └── test_tasks.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── docker-compose.yml
├── Makefile
├── pytest.ini
├── example.env
└── README.md
```

### Полезные команды

```bash
# Логи
make logs              # Все сервисы
make logs-backend      # Только backend
make logs-celery       # Только Celery

# Линтинг и форматирование
make lint              # Проверка кода
make format            # Форматирование black

# Очистка
make clean             # Удалить временные файлы

# Celery
make celery-status     # Статус воркеров
make celery-inspect    # Активные задачи
```

### Добавление новых зависимостей

1. Добавьте пакет в `backend/requirements.txt`
2. Пересоберите образы: `make build`
3. Перезапустите: `make restart`

## 🔒 Безопасность

### Реализованные меры

- ✅ Валидация URL (только Coub.com)
- ✅ Санитизация имён файлов
- ✅ Защита от path traversal
- ✅ Rate limiting (10 запросов/минуту)
- ✅ Ограничение размера файлов (100 MB)
- ✅ CORS настройки
- ✅ UUID префиксы для файлов

### Рекомендации для production

1. Измените `SECRET_KEY` в `.env`
2. Настройте `ALLOWED_ORIGINS` для вашего домена
3. Используйте HTTPS
4. Настройте firewall для БД и Redis
5. Включите Sentry для мониторинга ошибок
6. Регулярно обновляйте зависимости

## 📊 Мониторинг

### Health checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/redis
```

### Celery мониторинг

Раскомментируйте секцию `flower` в `docker-compose.yml` и перезапустите:

```bash
docker-compose up -d flower
```

Откройте http://localhost:5555

## 🐛 Troubleshooting

### Проблема: База данных недоступна

```bash
# Проверьте статус
docker-compose ps

# Пересоздайте контейнер
docker-compose down
docker-compose up -d db
```

### Проблема: Celery не обрабатывает задачи

```bash
# Проверьте логи
make logs-celery

# Перезапустите воркер
docker-compose restart celery_worker
```

### Проблема: Файл не скачивается

```bash
# Проверьте права на директорию
ls -la ./downloads/

# Создайте директорию если нет
mkdir -p ./downloads
chmod 777 ./downloads
```

## 📈 Производительность

- Асинхронная обработка запросов (FastAPI)
- Connection pooling для БД
- Redis для кэширования результатов
- Celery для параллельной загрузки файлов
- Оптимизированные Docker образы

## 🤝 Contributing

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Перед отправкой PR

```bash
make format    # Отформатируйте код
make lint      # Проверьте линтером
make test      # Запустите тесты
```

## 📝 License

MIT License

## 👥 Authors

Ваше имя - [GitHub](https://github.com/yourusername)

## 🙏 Acknowledgments

- FastAPI за отличный фреймворк
- Celery за надёжную очередь задач
- Vue.js за простой и мощный frontend
