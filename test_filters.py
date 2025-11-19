#!/usr/bin/env python3
import httpx
import time

BASE_URL = "http://localhost:8000"

# Получить токен
email = f"test_{int(time.time())}@example.com"
password = "SecureTest123!@#"

client = httpx.Client(base_url=BASE_URL, timeout=30.0)

# Sign up
print("Signing up...")
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
print("Signing in...")
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

# Создать тестовые заметки
print("=== СОЗДАНИЕ ТЕСТОВЫХ ЗАМЕТОК ===")

test_notes = [
    {
        "title": "Заметка про Даню",
        "tags": "test,personal",
        "text_notes": "Привет, меня зовут Даня",
    },
    {
        "title": "Рабочая встреча",
        "tags": "work,meeting",
        "text_notes": "Обсуждение проекта",
    },
    {
        "title": "Тестовая заметка",
        "tags": "test",
        "text_notes": "Это тестовая заметка для проверки фильтров",
    },
    {
        "title": "Важная задача",
        "tags": "work,important",
        "text_notes": "Срочная задача на сегодня",
    },
]

created_ids = []
for note_data in test_notes:
    response = client.post("/api/notes", json=note_data, headers=headers)
    if response.status_code == 201:
        note = response.json()
        created_ids.append(note["id"])
        print(f"✓ Created: {note['id']} - {note['title']}")
    else:
        print(f"✗ Failed: {response.status_code} - {note_data['title']}")

print(f"\n✅ Created {len(created_ids)}/{len(test_notes)} notes\n")

# Тесты фильтрации
print("=" * 60)
print("ТЕСТИРОВАНИЕ ФИЛЬТРОВ")
print("=" * 60)

print("\n📋 TEST 1: Получить все заметки")
response = client.get("/api/notes", headers=headers)
notes = response.json()
print(f"   Status: {response.status_code} | Found: {len(notes)} notes")
for note in notes[:3]:
    print(f"   - {note['id']}: {note['title']}")

print("\n📅 TEST 2: Фильтрация по датам (сегодня)")
response = client.get(
    "/api/notes",
    params={"date_from": "2025-11-19T00:00:00", "date_to": "2025-11-19T23:59:59"},
    headers=headers,
)
print(f"   Status: {response.status_code} | Found: {len(response.json())} notes")

print("\n🔍 TEST 3: Full-text search ('даня')")
response = client.get("/api/notes", params={"search": "даня"}, headers=headers)
results = response.json()
print(f"   Status: {response.status_code} | Found: {len(results)} notes")
if results:
    print(f"   ✓ Match: {results[0]['title']}")

print("\n🔍 TEST 4: Full-text search ('тестовая')")
response = client.get("/api/notes", params={"search": "тестовая"}, headers=headers)
results = response.json()
print(f"   Status: {response.status_code} | Found: {len(results)} notes")
if results:
    print(f"   ✓ Match: {results[0]['title']}")

print("\n🏷️  TEST 5: Фильтрация по tags ('test')")
response = client.get("/api/notes", params={"tags": "test"}, headers=headers)
print(
    f"   Status: {response.status_code} | Found: {len(response.json())} notes with tag 'test'"
)

print("\n🏷️  TEST 6: Фильтрация по tags ('work')")
response = client.get("/api/notes", params={"tags": "work"}, headers=headers)
results = response.json()
print(
    f"   Status: {response.status_code} | Found: {len(results)} notes with tag 'work'"
)
for note in results:
    print(f"   - {note['title']}")

print("\n⬆️  TEST 7: Сортировка по title (ASC)")
response = client.get(
    "/api/notes", params={"sort_by": "title", "order": "asc"}, headers=headers
)
results = response.json()
print(f"   Status: {response.status_code} | Sorted results:")
for note in results:
    print(f"   - {note['title']}")

print("\n⬇️  TEST 8: Сортировка по title (DESC)")
response = client.get(
    "/api/notes", params={"sort_by": "title", "order": "desc"}, headers=headers
)
results = response.json()
print(f"   Status: {response.status_code} | Sorted results:")
for note in results:
    print(f"   - {note['title']}")

print("\n🔗 TEST 9: Комбинация фильтров (search + tags + sort)")
response = client.get(
    "/api/notes",
    params={
        "search": "заметка",
        "tags": "test",
        "sort_by": "created_at",
        "order": "desc",
    },
    headers=headers,
)
results = response.json()
print(f"   Status: {response.status_code} | Found: {len(results)} notes")
for note in results:
    print(f"   - {note['id']}: {note['title']} (tags: {note['tags']})")

print("\n📄 TEST 10: Пагинация (limit=2, skip=0)")
response = client.get("/api/notes", params={"limit": 2, "skip": 0}, headers=headers)
print(f"   Status: {response.status_code} | Page 1: {len(response.json())} notes")

print("\n📄 TEST 11: Пагинация (limit=2, skip=2)")
response = client.get("/api/notes", params={"limit": 2, "skip": 2}, headers=headers)
print(f"   Status: {response.status_code} | Page 2: {len(response.json())} notes")

print("\n" + "=" * 60)
print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ!")
print("=" * 60)
