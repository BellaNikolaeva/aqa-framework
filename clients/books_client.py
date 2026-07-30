from clients.base_client import BaseClient


class BooksClient(BaseClient):
    def list(self, **query_params):
        return self.get("/api/books/", params=query_params)

    def create(self, **book_data):
        return self.post("/api/books/", json=book_data)

    def get_by_id(self, book_id: int):
        return self.get(f"/api/books/{book_id}/")

    def update(self, book_id: int, **book_data):
        return self.put(f"/api/books/{book_id}/", json=book_data)

    def partial_update(self, book_id: int, **book_data):
        return self.patch(f"/api/books/{book_id}/", json=book_data)

    def delete_book(self, book_id: int):
        # Имя отличается от HTTP-метода delete() базового клиента,
        # иначе получим бесконечную рекурсию через self.delete().
        return super().delete(f"/api/books/{book_id}/")

    def search(
        self,
        query: str = None,
        genre: str = None,
        tag: str = None,
        year_from: int = None,
        year_to: int = None,
    ):
        params = {
            k: v
            for k, v in {
                "search": query,
                "genre": genre,
                "tag": tag,
                "year_from": year_from,
                "year_to": year_to,
            }.items()
            if v is not None
        }
        return self.get("/api/books/", params=params)
