# 🚀 Быстрый старт Audio Notes App

## За 5 минут до первой аудиозаметки

### Шаг 1: Подготовка (2 минуты)

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd audio-notes-app

# 2. Скопируйте .env.example в .env
cp .env.example .env

# 3. Откройте .env и добавьте API ключи
# Получить ключи:
# - Deepgram: https://console.deepgram.com/
# - Gemini: https://makersuite.google.com/app/apikey

nano .env  # или vim, или любой редактор
```

**Обязательно заполните:**
```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### Шаг 2: Запуск (1 минута)

```bash
# Запустить все сервисы
docker-compose up -d

# Дождаться запуска (30 секунд)
sleep 30

# Проверить что работает
curl http://localhost:8000/health
```

Должны увидеть:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

### Шаг 3: Первый тест (2 минуты)

**Вариант A: Автоматический тест**

```bash
# Запустить тест с вашим аудиофайлом
python3 simple_audio_test.py path/to/your/audio.wav
```

Скрипт автоматически:
- ✅ Зарегистрирует пользователя
- ✅ Создаст заметку
- ✅ Загрузит аудио
- ✅ Дождется обработки
- ✅ Выведет результат

**Вариант B: Через Swagger UI**

1. Откройте http://localhost:8000/docs
2. Найдите `POST /auth/register`
3. Нажмите "Try it out"
4. Введите:
   ```json
   {
     "email": "test@example.com",
     "password": "Password123!"
   }
   ```
5. Нажмите "Execute"
6. Скопируйте `access_token`
7. Нажмите кнопку **"Authorize"** (🔓) вверху
8. Вставьте токен → "Authorize" → "Close"
9. Теперь можете создавать заметки!

---

## 📖 Примеры использования

### Пример 1: Быстрая заметка

```bash
python3 simple_audio_test.py meeting.wav --title "Встреча 20 января"
```

### Пример 2: С существующим аккаунтом

```bash
python3 simple_audio_test.py audio.wav \
  --email user@example.com \
  --password MyPassword123
```

### Пример 3: Через API

```bash
# 1. Получить токен
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"api@example.com","password":"Pass123!"}' | jq -r '.access_token')

# 2. Создать заметку
NOTE=$(curl -s -X POST "http://localhost:8000/api/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"API Test","tags":"api","text_notes":"Testing"}' | jq -r '.id')

# 3. Загрузить аудио (используйте Python скрипт или WebSocket)
python3 simple_audio_test.py audio.wav --token "$TOKEN" --note-id $NOTE

# 4. Проверить результат
curl -s "http://localhost:8000/api/notes/$NOTE" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## 🎯 Что дальше?

### Изучите документацию

- **Полная документация:** [README.md](README.md)
- **Swagger UI:** http://localhost:8000/docs
- **Технические детали:** [SWAGGER_AUTH_IMPLEMENTATION.md](SWAGGER_AUTH_IMPLEMENTATION.md)

### Попробуйте функции

**Поиск и фильтрация:**
```bash
# Найти заметки с тегом "работа"
curl "http://localhost:8000/api/notes?tags=работа" \
  -H "Authorization: Bearer $TOKEN"

# Полнотекстовый поиск
curl "http://localhost:8000/api/notes?search=встреча" \
  -H "Authorization: Bearer $TOKEN"

# Только завершенные заметки
curl "http://localhost:8000/api/notes?status=completed" \
  -H "Authorization: Bearer $TOKEN"
```

**CRUD операции:**
```bash
# Создать
curl -X POST "http://localhost:8000/api/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Новая заметка","tags":"тест","text_notes":"Описание"}'

# Прочитать
curl "http://localhost:8000/api/notes/1" \
  -H "Authorization: Bearer $TOKEN"

# Обновить
curl -X PUT "http://localhost:8000/api/notes/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Обновленная заметка","tags":"тест,обновлено","text_notes":"Новое описание"}'

# Удалить
curl -X DELETE "http://localhost:8000/api/notes/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Запустите тесты

```bash
# Полный тест авторизации + заметки + аудио
python3 test_full_flow_with_auth.py

# Тест только авторизации
bash test_complete_auth.sh

# Unit тесты
uv sync --extra test
uv run pytest
```

---

## 🔧 Troubleshooting

### Backend не запускается

```bash
# Проверить логи
docker-compose logs backend

# Пересобрать контейнеры
docker-compose build --no-cache
docker-compose up -d
```

### Ошибка "API key required"

Проверьте `.env` файл:
```bash
cat .env | grep -E "(DEEPGRAM|GEMINI)"
```

Должны быть заполнены:
```
DEEPGRAM_API_KEY=<ваш_ключ>
GEMINI_API_KEY=<ваш_ключ>
```

### Аудио не обрабатывается

```bash
# Проверить worker
docker logs audio-notes-worker

# Проверить формат аудио
ffprobe your_audio.wav

# Конвертировать в поддерживаемый формат
ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav
```

---

## 📞 Помощь

- **Документация:** [README.md](README.md)
- **Issues:** https://github.com/urasinovjr/audio-notes-app/issues
- **Swagger API:** http://localhost:8000/docs

---

## ⚡ Быстрые команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Логи
docker logs -f audio-notes-backend

# Тест
python3 simple_audio_test.py audio.wav

# Swagger
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/health

# Список заметок
curl "http://localhost:8000/api/notes" -H "Authorization: Bearer $TOKEN"
```

---

**Готово! Начните использовать Audio Notes App прямо сейчас! 🎉**
