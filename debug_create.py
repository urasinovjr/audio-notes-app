#!/usr/bin/env python3
import httpx
import time
import json

BASE_URL = "http://localhost:8000"

# Получить токен
email = f"test_{int(time.time())}@example.com"
password = "SecureTest123!@#"

client = httpx.Client(base_url=BASE_URL)

# Sign up
client.post(
    "/auth/signup",
    json={
        "formFields": [
            {"id": "email", "value": email},
            {"id": "password", "value": password},
        ]
    },
)

# Sign in
response = client.post(
    "/auth/signin",
    json={
        "formFields": [
            {"id": "email", "value": email},
            {"id": "password", "value": password},
        ]
    },
)

token = response.headers.get("st-access-token")
headers = {"Authorization": f"Bearer {token}"}

print(f"✓ Authenticated as: {email}\n")

# Создать тестовую заметку с ДЕТАЛЬНЫМ выводом
print("=== ТЕСТ СОЗДАНИЯ ЗАМЕТКИ ===")

test_note = {
    "title": "Заметка про Даню",
    "tags": "test,personal",
    "text_notes": "Привет, меня зовут Даня",
}

print(f"Отправляем данные:")
print(json.dumps(test_note, indent=2, ensure_ascii=False))

response = client.post("/api/notes", json=test_note, headers=headers)

print(f"\nОтвет сервера:")
print(f"Status: {response.status_code}")
print(f"Body:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

if response.status_code == 201:
    print("\n✅ Заметка создана успешно!")
else:
    print("\n❌ Ошибка создания заметки")
    print("\nПодробности ошибки:")
    error_details = response.json()
    if "detail" in error_details:
        print(json.dumps(error_details["detail"], indent=2, ensure_ascii=False))
