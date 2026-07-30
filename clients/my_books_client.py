from clients.base_client import BaseClient


class MyBooksClient(BaseClient):
    def list(self, status: str = None):
        params = {"status": status} if status else {}
        return self.get("/api/my-books/", params=params)

    def add(self, book_id: int, status: str = "want_to_read", **extra):
        # Поле называется book_id, не book — подтверждено реальным ответом
        # API: {"book_id": ["Обязательное поле."]} при отправке "book".
        payload = {"book_id": book_id, "status": status, **extra}
        return self.post("/api/my-books/", json=payload)

    def get_by_id(self, entry_id: int):
        return self.get(f"/api/my-books/{entry_id}/")

    def update_entry(self, entry_id: int, **fields):
        return self.patch(f"/api/my-books/{entry_id}/", json=fields)

    def remove(self, entry_id: int):
        return super().delete(f"/api/my-books/{entry_id}/")

    def stats(self):
        return self.get("/api/my-books/stats/")
