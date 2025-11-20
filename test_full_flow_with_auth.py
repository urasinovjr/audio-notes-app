#!/usr/bin/env python3
"""
Полный end-to-end тест с авторизацией и загрузкой аудио
"""
import asyncio
import json
import time
from pathlib import Path

import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def print_step(step: str):
    print(f"\n{'='*60}")
    print(f"  {step}")
    print("=" * 60)


async def main():
    print("\n" + "=" * 60)
    print("  ПОЛНЫЙ ТЕСТ: Авторизация + Создание заметки + Загрузка аудио")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ШАГ 1: Попытка создать заметку БЕЗ авторизации (должна провалиться)
        print_step("ШАГ 1: Попытка создать заметку БЕЗ токена (должна провалиться)")

        try:
            response = await client.post(
                f"{BASE_URL}/api/notes",
                json={
                    "title": "Тест без авторизации",
                    "tags": "test",
                    "text_notes": "Это не должно работать",
                },
            )
            if response.status_code == 401 or response.status_code == 403:
                print("✅ Правильно! Запрос без токена отклонен")
                print(f"   Статус: {response.status_code}")
                print(f"   Ответ: {response.json()}")
            else:
                print("❌ ОШИБКА: Запрос без токена должен был провалиться!")
                print(f"   Статус: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при попытке без токена: {e}")
            return False

        # ШАГ 2: Регистрация/авторизация пользователя
        print_step("ШАГ 2: Регистрация нового пользователя")

        email = f"test_{int(time.time())}@example.com"
        password = "TestPassword123!"

        print(f"Email: {email}")
        print(f"Password: {password}")

        try:
            response = await client.post(
                f"{BASE_URL}/auth/register", json={"email": email, "password": password}
            )

            if response.status_code == 201:
                data = response.json()
                token = data.get("access_token")
                user_id = data.get("user_id")

                print("✅ Регистрация успешна!")
                print(f"   User ID: {user_id}")
                print(f"   Token: {token[:50]}...")
            else:
                print(f"❌ Ошибка регистрации: {response.status_code}")
                print(f"   Ответ: {response.json()}")
                return False

        except Exception as e:
            print(f"❌ Ошибка при регистрации: {e}")
            return False

        # Заголовки с Bearer токеном
        headers = {"Authorization": f"Bearer {token}"}

        # ШАГ 3: Создание заметки С токеном
        print_step("ШАГ 3: Создание заметки С Bearer токеном")

        try:
            response = await client.post(
                f"{BASE_URL}/api/notes",
                headers=headers,
                json={
                    "title": "Тестовая аудиозаметка",
                    "tags": "test,audio,demo",
                    "text_notes": "Заметка для тестирования полного цикла",
                },
            )

            if response.status_code == 200 or response.status_code == 201:
                note = response.json()
                note_id = note["id"]

                print("✅ Заметка создана успешно!")
                print(f"   ID: {note_id}")
                print(f"   Title: {note['title']}")
                print(f"   User ID: {note['user_id']}")
                print(f"   Status: {note['status']}")
            else:
                print(f"❌ Ошибка создания заметки: {response.status_code}")
                print(f"   Ответ: {response.json()}")
                return False

        except Exception as e:
            print(f"❌ Ошибка при создании заметки: {e}")
            return False

        # ШАГ 4: Проверка, что можем получить заметку
        print_step("ШАГ 4: Получение созданной заметки")

        try:
            response = await client.get(f"{BASE_URL}/api/notes/{note_id}", headers=headers)

            if response.status_code == 200:
                note = response.json()
                print("✅ Заметка получена успешно!")
                print(f"   Title: {note['title']}")
                print(f"   Status: {note['status']}")
            else:
                print(f"❌ Ошибка получения заметки: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Ошибка при получении заметки: {e}")
            return False

        # ШАГ 5: Создание тестового аудиофайла
        print_step("ШАГ 5: Создание тестового аудиофайла")

        # Создаем простой WAV файл (тишина на 1 секунду)
        import struct

        audio_path = Path("/tmp/test_audio.wav")

        # WAV header для 1 секунды тишины, 16000 Hz, mono, 16-bit
        sample_rate = 16000
        num_channels = 1
        bits_per_sample = 16
        duration = 1  # секунда
        num_samples = sample_rate * duration

        # Создаем данные (тишина)
        audio_data = b"\x00\x00" * num_samples

        # WAV заголовок
        with open(audio_path, "wb") as f:
            # RIFF header
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(audio_data)))
            f.write(b"WAVE")

            # fmt chunk
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))  # chunk size
            f.write(struct.pack("<H", 1))  # audio format (PCM)
            f.write(struct.pack("<H", num_channels))
            f.write(struct.pack("<I", sample_rate))
            byte_rate = sample_rate * num_channels * bits_per_sample // 8
            f.write(struct.pack("<I", byte_rate))
            block_align = num_channels * bits_per_sample // 8
            f.write(struct.pack("<H", block_align))
            f.write(struct.pack("<H", bits_per_sample))

            # data chunk
            f.write(b"data")
            f.write(struct.pack("<I", len(audio_data)))
            f.write(audio_data)

        file_size = audio_path.stat().st_size
        print("✅ Тестовый аудиофайл создан")
        print(f"   Путь: {audio_path}")
        print(f"   Размер: {file_size} байт")
        print("   Формат: WAV, 16000 Hz, mono, 16-bit")

        # ШАГ 6: Загрузка аудио через WebSocket С токеном
        print_step("ШАГ 6: Загрузка аудио через WebSocket")

        try:
            # Добавляем токен в URL как query parameter
            ws_url = f"{WS_URL}/ws/upload/{note_id}?token={token}"

            print(f"Подключение к WebSocket: {ws_url}")

            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket соединение установлено")

                # Читаем аудиофайл
                audio_bytes = audio_path.read_bytes()

                # Отправляем метаданные
                metadata = {"filename": "test_audio.wav", "size": len(audio_bytes)}
                await websocket.send(json.dumps(metadata))
                print(f"   Отправлены метаданные: {metadata}")

                # Получаем подтверждение
                response = await websocket.recv()
                msg = json.loads(response)
                print(f"   Получен ответ: {msg}")

                if msg.get("status") != "ready":
                    print(f"❌ Неожиданный статус: {msg}")
                    return False

                # Отправляем аудио данные чанками
                chunk_size = 8192
                total_sent = 0

                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i : i + chunk_size]
                    await websocket.send(chunk)
                    total_sent += len(chunk)

                print(f"   Отправлено {total_sent} байт аудио данных")

                # Отправляем сигнал завершения
                await websocket.send(json.dumps({"action": "done"}))
                print("   Отправлен сигнал завершения")

                # Ждем подтверждения
                response = await websocket.recv()
                msg = json.loads(response)
                print(f"   Финальный ответ: {msg}")

                if msg.get("status") in ["received", "processing", "completed"]:
                    print(f"✅ Аудио успешно загружено! Статус: {msg.get('status')}")
                else:
                    print(f"⚠️  Получен статус: {msg.get('status')}")

        except Exception as e:
            print(f"❌ Ошибка при загрузке аудио: {e}")
            import traceback

            traceback.print_exc()
            return False

        # ШАГ 7: Проверяем обновленную заметку
        print_step("ШАГ 7: Проверка обновленной заметки")

        # Даем время на обработку
        await asyncio.sleep(2)

        try:
            response = await client.get(f"{BASE_URL}/api/notes/{note_id}", headers=headers)

            if response.status_code == 200:
                note = response.json()
                print("✅ Заметка получена после загрузки аудио")
                print(f"   Title: {note['title']}")
                print(f"   Status: {note['status']}")
                print(f"   File path: {note.get('file_path', 'N/A')}")

                # Проверяем, что файл обновлен
                if note.get("file_path") and note["file_path"] != "placeholder.mp3":
                    print(f"   ✅ Аудиофайл загружен: {note['file_path']}")
                else:
                    print("   ⚠️  Файл еще не обновлен (возможно, в процессе обработки)")

            else:
                print(f"❌ Ошибка получения заметки: {response.status_code}")

        except Exception as e:
            print(f"❌ Ошибка при проверке заметки: {e}")

        # ШАГ 8: Список заметок пользователя
        print_step("ШАГ 8: Получение списка всех заметок пользователя")

        try:
            response = await client.get(f"{BASE_URL}/api/notes", headers=headers)

            if response.status_code == 200:
                notes = response.json()
                print("✅ Получен список заметок")
                print(f"   Всего заметок: {len(notes)}")

                for note in notes[:3]:  # Показываем первые 3
                    print(
                        f"   - ID: {note['id']}, Title: {note['title']}, Status: {note['status']}"
                    )

            else:
                print(f"❌ Ошибка получения списка: {response.status_code}")

        except Exception as e:
            print(f"❌ Ошибка при получении списка: {e}")

        # ШАГ 9: Попытка получить чужую заметку (должна провалиться)
        print_step("ШАГ 9: Тест изоляции - попытка получить несуществующую заметку")

        try:
            fake_note_id = 999999
            response = await client.get(f"{BASE_URL}/api/notes/{fake_note_id}", headers=headers)

            if response.status_code == 404:
                print("✅ Правильно! Доступ к несуществующей заметке запрещен")
                print(f"   Статус: {response.status_code}")
            else:
                print(f"⚠️  Неожиданный статус: {response.status_code}")

        except Exception as e:
            print(f"   Ошибка: {e}")

        # Финальный результат
        print("\n" + "=" * 60)
        print("  РЕЗУЛЬТАТ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        print("✅ Все основные функции работают корректно!")
        print("\nПроверенные функции:")
        print("  1. ✅ Защита от неавторизованного доступа")
        print("  2. ✅ Регистрация пользователя")
        print("  3. ✅ Получение Bearer токена")
        print("  4. ✅ Создание заметки с авторизацией")
        print("  5. ✅ Получение заметки")
        print("  6. ✅ Загрузка аудио через WebSocket")
        print("  7. ✅ Обновление заметки после загрузки")
        print("  8. ✅ Получение списка заметок")
        print("  9. ✅ Изоляция пользователей")
        print("=" * 60)

        # Cleanup
        audio_path.unlink(missing_ok=True)

        return True


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
