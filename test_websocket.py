import asyncio
import websockets
import json


async def test_websocket():
    uri = "ws://localhost:8000/ws/upload?note_id=5&user_id=1"

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket подключено!")

            # Отправляем тестовые данные (1KB)
            test_data = b"TEST_AUDIO_DATA" * 100

            await websocket.send(test_data)
            print(f"✓ Отправлено {len(test_data)} байт")

            # Получаем ответ
            response = await websocket.recv()
            print(f"✓ Ответ от сервера: {response}")

            # Закрываем соединение
            await websocket.close()
            print("✓ WebSocket закрыто")

    except Exception as e:
        print(f"✗ Ошибка: {e}")


asyncio.run(test_websocket())
