"""
Нагрузочный смоук на каталог книг. Намеренно read-only: GET-запросы к
публичным эндпоинтам (/api/books/, /api/tags/) не требуют токена и не
оставляют мусорных данных в общем каталоге — в отличие от write-сценария,
который создавал бы записи в шаренной БД прод-сервиса при каждом прогоне.

Запуск с UI:
    locust -f locustfile.py --host https://book-tracker-api-frnm.onrender.com

Запуск headless (для разового отчёта, например локально перед релизом):
    locust -f locustfile.py --host https://book-tracker-api-frnm.onrender.com \
        --users 10 --spawn-rate 2 --run-time 30s --headless \
        --csv reports/load-test --html reports/load-test.html

Не запускается автоматически в CI на каждый push — только вручную
(workflow_dispatch, см. .github/workflows/ci.yml) или локально. Нагрузочное
тестирование на каждый коммит против общего prod-сервиса третьей стороны
(Render free tier) — не то, что нужно гонять молча в фоне.
"""

import random

from locust import HttpUser, between, task


class CatalogBrowsingUser(HttpUser):
    """Имитирует посетителя, который листает и ищет книги, не авторизуясь."""

    wait_time = between(1, 3)

    def on_start(self):
        # Прогреваем список известных id книг для последующих запросов
        # деталей — не читаем один и тот же id всё время.
        response = self.client.get("/api/books/", name="/api/books/ [list]")
        results = response.json().get("results", []) if response.ok else []
        self.known_book_ids = [book["id"] for book in results] or [1]

    @task(3)
    def list_books(self):
        self.client.get("/api/books/", name="/api/books/ [list]")

    @task(2)
    def search_books(self):
        # Общие слова из типичных названий — намеренно не случайные строки,
        # чтобы результат поиска был правдоподобным, а не всегда пустым.
        query = random.choice(["и", "о", "не", "жизнь", "время"])
        self.client.get(f"/api/books/?search={query}", name="/api/books/ [search]")

    @task(2)
    def get_book_detail(self):
        book_id = random.choice(self.known_book_ids)
        self.client.get(f"/api/books/{book_id}/", name="/api/books/{id}/ [detail]")

    @task(1)
    def list_tags(self):
        self.client.get("/api/tags/", name="/api/tags/ [list]")
