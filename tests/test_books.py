import allure
import pytest

from clients.books_client import BooksClient
from schemas.models import Book, PaginatedBooks
from utils.data_generator import random_book, random_tag_name


@allure.epic("Book Tracker API")
@allure.feature("Каталог книг")
class TestBooks:
    @allure.title("Создание книги возвращает 201 и корректную схему")
    @pytest.mark.smoke
    def test_create_book_success(self, books_client):
        payload = random_book()
        response = books_client.create(**payload)

        assert response.status_code == 201
        book = Book.model_validate(response.json())  # падает с понятной ошибкой, если контракт нарушен
        assert book.title == payload["title"]
        assert book.author == payload["author"]

        books_client.delete_book(book.id)

    @allure.title("Создание книги без обязательного поля возвращает 400")
    @pytest.mark.regression
    @pytest.mark.parametrize("missing_field", ["title", "author"])
    def test_create_book_missing_required_field(self, books_client, missing_field):
        # genre сюда не входит: по реальной схеме required для Book —
        # только author/created_at/id/tags/title (genre не обязателен).
        payload = random_book()
        del payload[missing_field]
        response = books_client.create(**payload)
        assert response.status_code == 400

    @allure.title("Список книг соответствует схеме пагинации")
    @pytest.mark.smoke
    def test_list_books_schema(self, books_client, created_book):
        response = books_client.list()
        assert response.status_code == 200
        PaginatedBooks.model_validate(response.json())

    @allure.title("Получение книги по id")
    @pytest.mark.smoke
    def test_get_book_by_id(self, books_client, created_book):
        response = books_client.get_by_id(created_book["id"])
        assert response.status_code == 200
        assert response.json()["id"] == created_book["id"]

    @allure.title("Получение несуществующей книги возвращает 404")
    @pytest.mark.regression
    def test_get_book_not_found(self, books_client):
        response = books_client.get_by_id(999_999_999)
        assert response.status_code == 404

    @allure.title("Частичное обновление книги (PATCH)")
    @pytest.mark.regression
    def test_partial_update_book(self, books_client, created_book):
        new_title = "Обновлённое название"
        response = books_client.partial_update(created_book["id"], title=new_title)
        assert response.status_code == 200
        assert response.json()["title"] == new_title

    @allure.title("Удаление книги — повторный GET возвращает 404")
    @pytest.mark.regression
    def test_delete_book(self, books_client):
        created = books_client.create(**random_book()).json()

        delete_response = books_client.delete_book(created["id"])
        assert delete_response.status_code == 204

        get_response = books_client.get_by_id(created["id"])
        assert get_response.status_code == 404

    @allure.title("Поиск книг по названию находит созданную книгу")
    @pytest.mark.regression
    def test_search_by_title(self, books_client, created_book):
        response = books_client.search(query=created_book["title"])
        assert response.status_code == 200
        results = response.json()["results"]
        assert any(book["id"] == created_book["id"] for book in results)

    @allure.title("Фильтр по жанру возвращает только книги этого жанра")
    @pytest.mark.regression
    def test_filter_by_genre(self, books_client, created_book):
        response = books_client.search(genre=created_book["genre"])
        assert response.status_code == 200
        results = response.json()["results"]
        assert all(book["genre"] == created_book["genre"] for book in results)

    @allure.title("Запрос без токена авторизации возвращает 401")
    @pytest.mark.regression
    def test_unauthenticated_request_rejected(self):
        anonymous_client = BooksClient()
        response = anonymous_client.create(**random_book())
        assert response.status_code == 401

    @allure.title("Книга, созданная с tag_ids, возвращает вложенные теги в ответе")
    @pytest.mark.smoke
    def test_create_book_with_tags(self, books_client, tags_client):
        tag = tags_client.create(name=random_tag_name()).json()
        payload = random_book()
        payload["tag_ids"] = [tag["id"]]

        response = books_client.create(**payload)
        assert response.status_code == 201
        book = Book.model_validate(response.json())
        assert tag["id"] in [t.id for t in book.tags]

        books_client.delete_book(book.id)
        tags_client.remove(tag["id"])

    @allure.title("Фильтр по тегу возвращает только книги с этим тегом")
    @pytest.mark.regression
    def test_filter_by_tag(self, books_client, tags_client):
        tag = tags_client.create(name=random_tag_name()).json()
        payload = random_book()
        payload["tag_ids"] = [tag["id"]]
        book = books_client.create(**payload).json()

        response = books_client.search(tag=tag["name"])
        assert response.status_code == 200
        results = response.json()["results"]
        assert any(b["id"] == book["id"] for b in results)

        books_client.delete_book(book["id"])
        tags_client.remove(tag["id"])

    @allure.title("Фильтр по диапазону года издания (year_from/year_to)")
    @pytest.mark.regression
    def test_filter_by_year_range(self, books_client):
        payload = random_book()
        payload["year_published"] = 1975
        book = books_client.create(**payload).json()

        in_range = books_client.search(year_from=1970, year_to=1980).json()["results"]
        assert any(b["id"] == book["id"] for b in in_range)

        out_of_range = books_client.search(year_from=2020, year_to=2026).json()["results"]
        assert all(b["id"] != book["id"] for b in out_of_range)

        books_client.delete_book(book["id"])
