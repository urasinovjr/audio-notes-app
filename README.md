# 🎙️ Audio Notes App

[![CI/CD Pipeline](https://github.com/urasinovjr/audio-notes-app/actions/workflows/ci.yml/badge.svg)](https://github.com/urasinovjr/audio-notes-app/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-77%20passing-success.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-43%25-yellow.svg)]()
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

## Описание проекта

Веб-приложение для управления аудио-заметками с автоматической транскрибацией (Deepgram) и суммаризацией (Google Gemini AI).

## ✨ Основные возможности

### Управление заметками
- ✅ CRUD операции (создание, чтение, обновление, удаление)
- ✅ Загрузка аудио-файлов через WebSocket
- ✅ Автоматическая транскрибация аудио в текст
- ✅ Автоматическая суммаризация текста

### Поиск и фильтрация
- ✅ Full-text поиск (case-insensitive)
- ✅ Фильтрация по статусу (pending, processing, completed)
- ✅ Фильтрация по тегам
- ✅ Фильтрация по датам
- ✅ Сортировка (по дате создания, названию, статусу)
- ✅ Пагинация

### Авторизация
- ✅ SuperTokens integration
- ✅ JWT authentication
- ✅ Изоляция данных между пользователями

### Безопасность
- ✅ Rate limiting (10-50 запросов/минуту)
- ✅ CORS настройки
- ✅ Security headers (6 headers)
- ✅ Input validation
- ✅ Error handling с retry logic

## 🏗️ Архитектура

### Технологический стек
- **Backend:** Python 3.11, FastAPI
- **Database:** PostgreSQL 15
- **Message Queue:** RabbitMQ
- **Authentication:** SuperTokens
- **AI Services:** Deepgram (STT), Google Gemini (Summarization)
- **Deployment:** Docker Compose
- **CI/CD:** GitHub Actions

### Микросервисная архитектура (6 сервисов)
1. **backend** - FastAPI REST API + WebSocket server
2. **worker** - Background workers для обработки аудио
3. **postgres** - Основная база данных
4. **postgres-test** - Тестовая база данных
5. **rabbitmq** - Message broker
6. **supertokens** + **supertokens-db** - Авторизация

### Структура проекта

```
audio-notes-app/
├── .github/
│   └── workflows/
│       ├── ci.yml                      # CI/CD pipeline
│       ├── pr-checks.yml               # PR validation
│       └── dependency-review.yml       # Security checks
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── audio_notes.py          # REST API endpoints
│   │       └── websocket.py            # WebSocket upload
│   ├── auth/
│   │   ├── config.py                   # SuperTokens config
│   │   ├── dependencies.py             # Auth dependencies
│   │   └── hooks.py                    # Auth lifecycle hooks
│   ├── core/
│   │   ├── config.py                   # Settings & env validation
│   │   ├── exceptions.py               # Custom exceptions
│   │   ├── rate_limit.py               # Rate limiting
│   │   └── security.py                 # Security headers
│   ├── db/
│   │   ├── database.py                 # DB connection
│   │   └── models.py                   # SQLAlchemy models
│   ├── schemas/
│   │   └── audio_note.py               # Pydantic schemas
│   ├── services/
│   │   ├── audio_note.py               # Business logic
│   │   └── queue.py                    # RabbitMQ service
│   ├── workers/
│   │   ├── transcription_worker.py     # Deepgram worker
│   │   └── summarization_worker.py     # Gemini worker
│   └── main.py                         # FastAPI app
├── tests/
│   ├── conftest.py                     # Test fixtures
│   ├── test_api_notes.py               # API tests (18)
│   ├── test_auth.py                    # Auth tests (19)
│   ├── test_filters.py                 # Filter tests (18)
│   ├── test_websocket.py               # WebSocket tests (17)
│   └── test_workers.py                 # Worker tests (5)
├── migrations/                         # Alembic migrations
├── docker-compose.yml                  # Docker orchestration
├── Dockerfile                          # Backend image
├── Dockerfile.worker                   # Worker image
├── pyproject.toml                      # Dependencies (uv)
├── pytest.ini                          # Test configuration
├── .ruff.toml                          # Linting config
├── .pre-commit-config.yaml             # Git hooks
├── codecov.yml                         # Coverage config
└── README.md                           # This file
```

## 🚀 Быстрый старт

### Предварительные требования
- Docker & Docker Compose
- Python 3.11+
- uv (package manager)

### 1. Клонировать репозиторий

```bash
git clone https://github.com/urasinovjr/audio-notes-app.git
cd audio-notes-app
```

### 2. Настроить окружение

```bash
# Скопировать .env.example
cp .env.example .env

# Отредактировать .env (добавить API ключи)
# DEEPGRAM_API_KEY=your_deepgram_key
# GEMINI_API_KEY=your_gemini_key
```

### 3. Запустить приложение

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f backend
```

### 4. Открыть документацию API

```
http://localhost:8000/docs
```

## 🧪 Тестирование

### Установка зависимостей

```bash
# Установить с тестовыми зависимостями
uv sync --extra test
```

### Запуск тестов

```bash
# Все тесты
uv run pytest tests/ -v

# Конкретный модуль
uv run pytest tests/test_api_notes.py -v

# С coverage
uv run pytest tests/ --cov=app --cov-report=html

# Открыть HTML отчет
open htmlcov/index.html
```

### Статистика тестов
- **Всего тестов:** 77
- **Coverage:** 43%
- **API endpoints:** 65% покрытие
- **Services:** 72% покрытие
- **Models:** 93% покрытие
- **Schemas:** 100% покрытие

### Структура тестов

```
tests/
├── conftest.py                 # Фикстуры (test_user, client, db_session)
├── test_api_notes.py           # CRUD операции (18 тестов)
├── test_auth.py                # Авторизация и изоляция (19 тестов)
├── test_filters.py             # Фильтрация и поиск (18 тестов)
├── test_websocket.py           # WebSocket upload (17 тестов)
└── test_workers.py             # Background workers (5 тестов)
```

## 🔄 CI/CD

### GitHub Actions Workflows

1. **CI/CD Pipeline** (`.github/workflows/ci.yml`)
   - ✅ Linting (Ruff)
   - ✅ Tests (77 тестов)
   - ✅ Security scan (Trivy)
   - ✅ Docker build & push

2. **PR Checks** (`.github/workflows/pr-checks.yml`)
   - ✅ PR title validation (Conventional Commits)
   - ✅ Auto-labeling

3. **Dependency Review** (`.github/workflows/dependency-review.yml`)
   - ✅ Security vulnerability checks
   - ✅ License compliance

### Локальная разработка

```bash
# Установить pre-commit hooks
uv pip install pre-commit
pre-commit install

# Запустить linting вручную
uv run ruff check app/ tests/
uv run ruff format app/ tests/
```

## 📡 API Endpoints

### Заметки

```
GET    /api/notes          # Список заметок (с фильтрами)
POST   /api/notes          # Создать заметку
GET    /api/notes/{id}     # Получить заметку
PATCH  /api/notes/{id}     # Обновить заметку
DELETE /api/notes/{id}     # Удалить заметку
POST   /api/notes/{id}/upload-complete  # Завершить загрузку
```

### WebSocket

```
WS /ws/upload?note_id=X&user_id=Y  # Загрузка аудио-файла
```

### Параметры фильтрации
- `search` - полнотекстовый поиск (case-insensitive)
- `status` - фильтр по статусу (pending, processing, completed)
- `tags` - фильтр по тегам (comma-separated)
- `date_from` - фильтр от даты (ISO 8601)
- `date_to` - фильтр до даты (ISO 8601)
- `sort_by` - сортировка (created_at, title, status)
- `order` - порядок (asc, desc)
- `limit` - количество (default: 100)
- `skip` - пропустить (default: 0)

## 🔐 Безопасность

### Реализованные меры
- **Rate Limiting:** 10-50 запросов/минуту по endpoint
- **CORS:** Настроенные origins для frontend
- **Security Headers:** 6 headers (X-Frame-Options, CSP, HSTS, etc.)
- **Input Validation:** Pydantic validators для всех полей
- **Error Handling:** Глобальные exception handlers
- **Retry Logic:** 3 попытки для external API с exponential backoff

### Environment Variables
Все чувствительные данные в `.env`:
- `DEEPGRAM_API_KEY` - Deepgram API ключ
- `GEMINI_API_KEY` - Google Gemini API ключ
- `DATABASE_URL` - PostgreSQL connection string
- `RABBITMQ_URL` - RabbitMQ connection string
- `SUPERTOKENS_API_KEY` - SuperTokens ключ

## 📊 Мониторинг и логирование

### Loguru логирование
- Автоматическая ротация (7 дней)
- Structured logs (JSON)
- Логи для всех компонентов:
  - API requests/responses
  - Worker processing
  - External API calls
  - Errors and exceptions

### Просмотр логов

```bash
# Backend логи
docker logs audio-notes-backend -f

# Worker логи
docker logs audio-notes-worker -f

# RabbitMQ логи
docker logs audio-notes-rabbitmq -f
```

## 🛠️ Разработка

### Установка для разработки

```bash
# Установить с dev зависимостями
uv sync --extra dev

# Запустить pre-commit hooks
pre-commit install
```

### Создание миграций

```bash
# Создать новую миграцию
docker-compose exec backend alembic revision --autogenerate -m "description"

# Применить миграции
docker-compose exec backend alembic upgrade head
```

### Code Style
- **Linter:** Ruff
- **Formatter:** Ruff
- **Type Checker:** Mypy (опционально)
- **Conventions:** PEP 8

## 🤝 Contributing

### Workflow
1. Fork репозиторий
2. Создать feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'feat: add amazing feature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Открыть Pull Request

### Commit Messages
Используйте Conventional Commits:
- `feat:` - новая функциональность
- `fix:` - исправление бага
- `docs:` - изменения в документации
- `test:` - добавление тестов
- `refactor:` - рефакторинг кода
- `chore:` - прочие изменения

## 📄 Лицензия

Этот проект создан в рамках тестового задания

## 👤 Автор

**Даниил Урасинов**
