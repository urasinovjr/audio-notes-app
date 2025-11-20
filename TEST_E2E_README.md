# End-to-End Test - Документация

## Описание

`test_e2e.py` - полный end-to-end тест Audio Notes приложения, который проверяет:

1. ✅ Регистрацию/вход пользователя (SuperTokens)
2. ✅ Создание заметки с авторизацией
3. ✅ Загрузку аудио через WebSocket
4. ✅ Проверку статуса обработки заметки

## Использование

### Обычный запуск
```bash
python3 test_e2e.py
```

### С отладочной информацией
```bash
DEBUG=true python3 test_e2e.py
```

## Как работает авторизация

### Проблема
SuperTokens отправляет токены в **response headers**, а не в cookies:
- `st-access-token`
- `st-refresh-token`
- `front-token`

### Решение
1. Извлекаем токены из response headers после signin/signup
2. Преобразуем имена для Cookie header:
   - `st-access-token` → `sAccessToken`
   - `st-refresh-token` → `sRefreshToken`
   - `front-token` → `sFrontToken`
3. Отправляем обратно в Cookie header для последующих запросов

```python
# Извлечение токенов
tokens_dict = {}
token_mapping = {
    'st-access-token': 'sAccessToken',
    'st-refresh-token': 'sRefreshToken',
    'front-token': 'sFrontToken'
}

for header_name, cookie_name in token_mapping.items():
    if header_name in signin_response.headers:
        tokens_dict[cookie_name] = signin_response.headers[header_name]

# Использование токенов
cookie_header = '; '.join([f"{k}={v}" for k, v in tokens_dict.items()])
headers = {'Cookie': cookie_header}
requests.post(url, headers=headers, ...)
```

## Ожидаемые результаты

### Успешное выполнение
```
✅ PARTIAL SUCCESS! Тест выполнен успешно!
   Заметка создана и аудио загружено.
   Статус обработки: pending
```

**Примечание**: Статус `pending` - это нормально. Обработка аудио может занять несколько минут в зависимости от загрузки workers.

### Полный успех (если workers обработали заметку)
```
✅ SUCCESS! Все работает отлично!
   Заметка создана, аудио загружено и обработано!
```

## Проверка результатов

После выполнения теста можно проверить статус заметки:

```bash
# URL выводится в конце теста
curl http://localhost:8000/api/notes/{NOTE_ID} \
  -H "Cookie: sAccessToken=...; sRefreshToken=...; sFrontToken=..."
```

Или через браузер после входа в приложение.

## Требования

- Python 3.10+
- Библиотеки: `requests`, `websockets`
- Backend сервер должен быть запущен на `http://localhost:8000`
- Аудио файл: `uploads/test_audio_100.mp3`

## Устранение проблем

### Ошибка 401 (Unauthorized)
- Проверьте что SuperTokens сервис запущен
- Проверьте что токены правильно извлекаются (используйте `DEBUG=true`)

### Ошибка загрузки аудио
- Убедитесь что файл `uploads/test_audio_100.mp3` существует
- Проверьте права доступа к файлу

### Статус остается "pending" долго
- Проверьте что worker процессы запущены
- Проверьте логи workers для ошибок обработки
