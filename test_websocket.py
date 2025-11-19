#!/usr/bin/env python3
import httpx
import time

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

print(f"✓ Authenticated as: {email}")
print(f"✓ Token: {token[:50]}...\n")

# Создать тестовые заметки
print("=== СОЗДАНИЕ ТЕСТОВЫХ ЗАМЕТОК ===")

test_notes = [
    {
        "title": "Заметка про Даню",
        "tags": "test,personal",  # ← Строка, а не массив!
        "text_notes": "Привет, меня зовут Даня",
    },
    {
        "title": "Рабочая встреча",
        "tags": "work,meeting",  # ← Строка, а не массив!
        "text_notes": "Обсуждение проекта",
    },
    {
        "title": "Тестовая заметка",
        "tags": "test",  # ← Строка, а не массив!
        "text_notes": "Это тестовая заметка для проверки фильтров",
    },
]

created_ids = []
for note_data in test_notes:
    response = client.post("/api/notes", json=note_data, headers=headers)
    if response.status_code == 201:
        note = response.json()
        created_ids.append(note["id"])
        print(f"✓ Created note: {note['id']} - {note['title']}")
    else:
        print(f"✗ Failed to create note: {response.status_code}")
        print(f"  Error: {response.json()}")

print(f"\nCreated {len(created_ids)} notes\n")

# Тесты фильтрации
print("=== TEST 1: Получить все заметки ===")
response = client.get("/api/notes", headers=headers)
print(f"Status: {response.status_code}")
notes = response.json()
print(f"Results: {len(notes)} notes")
for note in notes:
    print(f"  - {note['id']}: {note['title']}")

print("\n=== TEST 2: Фильтрация по датам (сегодня) ===")
response = client.get(
    "/api/notes",
    params={"date_from": "2025-11-19T00:00:00", "date_to": "2025-11-19T23:59:59"},
    headers=headers,
)
print(f"Status: {response.status_code}")
print(f"Results: {len(response.json())} notes")

print("\n=== TEST 3: Full-text search (даня) ===")
response = client.get("/api/notes", params={"search": "даня"}, headers=headers)
print(f"Status: {response.status_code}")
results = response.json()
print(f"Results: {len(results)} notes")
if results:
    print(f"  Found: {results[0]['title']}")

print("\n=== TEST 4: Full-text search (тестовая) ===")
response = client.get("/api/notes", params={"search": "тестовая"}, headers=headers)
print(f"Status: {response.status_code}")
results = response.json()
print(f"Results: {len(results)} notes")
if results:
    print(f"  Found: {results[0]['title']}")

print("\n=== TEST 5: Фильтрация по tags ===")
response = client.get("/api/notes", params={"tags": "test"}, headers=headers)
print(f"Status: {response.status_code}")
print(f"Results: {len(response.json())} notes with tag 'test'")

print("\n=== TEST 6: Сортировка по title (ASC) ===")
response = client.get(
    "/api/notes", params={"sort_by": "title", "order": "asc"}, headers=headers
)
print(f"Status: {response.status_code}")
results = response.json()
print(f"Results (sorted by title):")
for note in results:
    print(f"  - {note['title']}")

print("\n=== TEST 7: Комбинация фильтров ===")
response = client.get(
    "/api/notes",
    params={
        "search": "test",
        "tags": "test",
        "sort_by": "created_at",
        "order": "desc",
        "limit": 10,
    },
    headers=headers,
)
print(f"Status: {response.status_code}")
results = response.json()
print(f"Results: {len(results)} notes")
for note in results:
    # tags возвращается как строка, разбить на массив для отображения
    tags = note["tags"].split(",") if note["tags"] else []
    print(f"  - {note['id']}: {note['title']} (tags: {', '.join(tags)})")

print("\n=== TEST 8: Пагинация ===")
response = client.get("/api/notes", params={"limit": 2, "skip": 0}, headers=headers)
print(f"Status: {response.status_code}")
print(f"Page 1 (limit=2, skip=0): {len(response.json())} notes")

response = client.get("/api/notes", params={"limit": 2, "skip": 2}, headers=headers)
print(f"Page 2 (limit=2, skip=2): {len(response.json())} notes")

print("\n✅ All filter tests completed!")
