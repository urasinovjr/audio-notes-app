#!/usr/bin/env python3
"""
Простой тест системы Audio Notes App

Использование:
    python3 simple_audio_test.py path/to/audio.wav
    python3 simple_audio_test.py audio.wav --email user@example.com --password Pass123!
    python3 simple_audio_test.py audio.wav --note-id 5 --token "your_token"
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

try:
    import httpx
    import websockets
except ImportError:
    print("❌ Необходимо установить зависимости:")
    print("   pip install httpx websockets")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def print_header(text: str):
    """Красивый заголовок"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print("=" * 60)


def print_step(step: str, status: str = ""):
    """Печать шага с статусом"""
    symbols = {"ok": "✓", "error": "✗", "wait": "⟳", "info": "ℹ"}
    symbol = symbols.get(status, "•")
    print(f"{symbol} {step}")


async def check_backend():
    """Проверка что backend работает"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                return True
    except Exception:
        pass
    return False


async def register_or_login(email: str = None, password: str = None):
    """Регистрация или вход"""
    if not email:
        # Генерируем уникальный email
        timestamp = int(time.time())
        email = f"test_{timestamp}@example.com"
        password = "TestPassword123!"

    async with httpx.AsyncClient() as client:
        # Пробуем зарегистрироваться
        try:
            response = await client.post(
                f"{BASE_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=10.0,
            )

            if response.status_code == 201:
                data = response.json()
                return {"token": data["access_token"], "user_id": data["user_id"], "email": email}
        except Exception:
            pass

        # Если не получилось зарегистрироваться, пробуем войти
        try:
            response = await client.post(
                f"{BASE_URL}/auth/token", json={"email": email, "password": password}, timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                return {"token": data["access_token"], "user_id": data["user_id"], "email": email}
        except Exception:
            pass

    return None


async def create_note(token: str, title: str = "Тестовая аудиозаметка"):
    """Создание заметки"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "tags": "тест,аудио",
                "text_notes": "Заметка создана через simple_audio_test.py",
            },
            timeout=10.0,
        )

        if response.status_code in [200, 201]:
            return response.json()

    return None


async def upload_audio_websocket(token: str, note_id: int, audio_path: str):
    """Загрузка аудио через WebSocket"""
    audio_path = Path(audio_path)

    if not audio_path.exists():
        print_step(f"Файл не найден: {audio_path}", "error")
        return False

    # Читаем аудио файл
    audio_data = audio_path.read_bytes()
    file_size = len(audio_data)

    # Подключаемся к WebSocket
    uri = f"{WS_URL}/ws/upload/{note_id}?token={token}"

    try:
        async with websockets.connect(uri) as websocket:
            # 1. Отправляем метаданные
            metadata = {"filename": audio_path.name, "size": file_size}
            await websocket.send(json.dumps(metadata))

            # 2. Ждем подтверждения
            response = await websocket.recv()
            msg = json.loads(response)

            if msg.get("status") != "ready":
                print_step(f"Ошибка WebSocket: {msg.get('message')}", "error")
                return False

            print_step(f"Загрузка аудио: {audio_path.name} ({file_size} байт)", "wait")

            # 3. Отправляем аудио чанками
            chunk_size = 8192
            total_sent = 0

            for i in range(0, file_size, chunk_size):
                chunk = audio_data[i : i + chunk_size]
                await websocket.send(chunk)
                total_sent += len(chunk)

                # Показываем прогресс
                progress = int((total_sent / file_size) * 100)
                if progress % 10 == 0:
                    print(f"   Прогресс: {progress}%", end="\r")

            print("   Прогресс: 100%")

            # 4. Отправляем сигнал завершения
            await websocket.send(json.dumps({"action": "done"}))

            # 5. Получаем финальный ответ
            response = await websocket.recv()
            msg = json.loads(response)

            if msg.get("status") in ["received", "processing", "completed"]:
                print_step("Аудио успешно загружено", "ok")
                return True
            else:
                print_step(f"Неожиданный статус: {msg.get('status')}", "error")
                return False

    except Exception as e:
        print_step(f"Ошибка при загрузке аудио: {e}", "error")
        return False


async def wait_for_processing(token: str, note_id: int, timeout: int = 120):
    """Ожидание обработки аудио"""
    start_time = time.time()
    last_status = None

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(
                    f"{BASE_URL}/api/notes/{note_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    note = response.json()
                    status = note.get("status")

                    if status != last_status:
                        print_step(f"Статус: {status}", "wait")
                        last_status = status

                    if status == "completed":
                        return note
                    elif status == "failed":
                        print_step("Обработка завершилась с ошибкой", "error")
                        return note

            except Exception as e:
                print_step(f"Ошибка при проверке статуса: {e}", "error")

            await asyncio.sleep(5)

    print_step(f"Превышен таймаут ожидания ({timeout} сек)", "error")
    return None


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Простой тест Audio Notes App")
    parser.add_argument("audio_file", help="Путь к аудиофайлу")
    parser.add_argument("--email", help="Email для входа (опционально)")
    parser.add_argument("--password", help="Пароль для входа (опционально)")
    parser.add_argument("--token", help="Существующий токен (опционально)")
    parser.add_argument("--note-id", type=int, help="ID существующей заметки (опционально)")
    parser.add_argument("--title", default="Тестовая аудиозаметка", help="Название заметки")

    args = parser.parse_args()

    # Проверяем что файл существует
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"❌ Файл не найден: {audio_path}")
        return 1

    print_header("ТЕСТ СИСТЕМЫ AUDIO NOTES APP")
    print(f"\nАудиофайл: {audio_path}")
    print(f"Размер: {audio_path.stat().st_size} байт")

    # 1. Проверка backend
    print_step("Проверка backend...", "wait")
    if not await check_backend():
        print_step("Backend не доступен на http://localhost:8000", "error")
        print("\nУбедитесь что сервисы запущены:")
        print("  docker-compose up -d")
        return 1
    print_step("Backend работает", "ok")

    # 2. Авторизация
    token = args.token
    note_id = args.note_id

    if not token:
        print_step("Авторизация...", "wait")
        auth_data = await register_or_login(args.email, args.password)

        if not auth_data:
            print_step("Не удалось авторизоваться", "error")
            return 1

        token = auth_data["token"]
        print_step(f"Пользователь: {auth_data['email']}", "ok")

    # 3. Создание заметки (если не указан note_id)
    if not note_id:
        print_step("Создание заметки...", "wait")
        note = await create_note(token, args.title)

        if not note:
            print_step("Не удалось создать заметку", "error")
            return 1

        note_id = note["id"]
        print_step(f"Заметка создана: ID={note_id}", "ok")

    # 4. Загрузка аудио
    print_header("ЗАГРУЗКА АУДИО")
    success = await upload_audio_websocket(token, note_id, audio_path)

    if not success:
        return 1

    # 5. Ожидание обработки
    print_header("ОБРАБОТКА АУДИО")
    print_step("Ожидание обработки (это может занять 30-120 секунд)...", "wait")

    result = await wait_for_processing(token, note_id, timeout=120)

    if not result:
        return 1

    # 6. Вывод результата
    print_header("РЕЗУЛЬТАТ")

    print("\n📝 ТРАНСКРИПЦИЯ:")
    print("-" * 60)
    transcription = result.get("transcription")
    if transcription:
        print(transcription)
    else:
        print("(нет транскрипции)")

    print("\n📋 САММАРИЗАЦИЯ:")
    print("-" * 60)
    summary = result.get("summary")
    if summary:
        print(summary)
    else:
        print("(нет саммаризации)")

    print("\n" + "=" * 60)
    print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
    print("=" * 60)

    print("\nИнформация о заметке:")
    print(f"  ID: {result.get('id')}")
    print(f"  Название: {result.get('title')}")
    print(f"  Статус: {result.get('status')}")
    print(f"  Файл: {result.get('file_path')}")

    print("\nПросмотр в Swagger UI:")
    print("  http://localhost:8000/docs#/Notes/get_audio_note_api_notes__note_id__get")
    print("\nAPI запрос:")
    print(f"  curl -X GET 'http://localhost:8000/api/notes/{note_id}' \\")
    print(f"    -H 'Authorization: Bearer {token[:30]}...'")

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
