#!/usr/bin/env python3
import httpx
import time

BASE_URL = "http://localhost:8000"

# Получить токен
email = f"test_{int(time.time())}@example.com"
password = "SecureTest123!@#"

client = httpx.Client(base_url=BASE_URL, timeout=30.0)

client.post(
    "/auth/signup",
    json={
        "formFields": [
            {"id": "email", "value": email},
            {"id": "password", "value": password},
        ]
    },
)

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

# Создать заметку
client.post(
    "/api/notes",
    json={
        "title": "Заметка про Даню",
        "tags": "test",
        "text_notes": "Привет, меня зовут Даня",
    },
    headers=headers,
)

print("=== ТЕСТ CASE-INSENSITIVE ПОИСКА ===\n")

test_cases = [
    ("даня", "строчные буквы"),
    ("Даня", "с большой буквы"),
    ("ДАНЯ", "все заглавные"),
    ("ДаНя", "смешанный регистр"),
    ("дан", "частичное совпадение"),
]

for search_query, description in test_cases:
    response = client.get(
        "/api/notes", params={"search": search_query}, headers=headers
    )
    results = response.json()
    found = len(results)

    if found > 0:
        print(f"✅ '{search_query}' ({description}): {found} results")
        print(f"   Match: {results[0]['title']}")
    else:
        print(f"❌ '{search_query}' ({description}): {found} results")
    print()

print("=== ТЕСТ ЗАВЕРШЕН ===")
