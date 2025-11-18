import asyncio
import websockets

async def upload_real_audio():
    note_id = 8
    audio_file_path = "uploads/test_audio_100.mp3"
    
    uri = f"ws://localhost:8000/ws/upload?note_id={note_id}&user_id=1"
    
    async with websockets.connect(uri) as websocket:
        print(f"✓ WebSocket подключено для note_id={note_id}")
        
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        print(f"✓ Файл прочитан: {len(audio_data)} байт")
        
        chunk_size = 8192
        total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            await websocket.send(chunk)
            response = await websocket.recv()
            chunk_num = i//chunk_size + 1
            print(f"✓ Chunk {chunk_num}/{total_chunks} отправлен")
        
        await websocket.close()
        print("✓ Загрузка завершена!")

asyncio.run(upload_real_audio())
