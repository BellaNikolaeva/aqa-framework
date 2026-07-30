import allure
import pytest

from schemas.models import UserBook
from utils.data_generator import random_user


@allure.epic("Book Tracker API")
@allure.feature("Личная библиотека")
class TestMyBooks:
    @allure.title("Добавление книги в библиотеку со статусом по умолчанию")
    @pytest.mark.smoke
    def test_add_book_default_status(self, my_books_client, created_book):
        response = my_books_client.add(book_id=created_book["id"])
        assert response.status_code == 201
        # Валидирует и структуру ответа: реальный API возвращает вложенный
        # объект book, а не book_id — book_id только для записи (writeOnly).
        entry = UserBook.model_validate(response.json())
        assert entry.status == "want_to_read"
        assert entry.book.id == created_book["id"]

    @allure.title("Изменение статуса на 'прочитано' позволяет проставить оценку")
    @pytest.mark.smoke
    def test_rate_book_after_marking_read(self, my_books_client, created_book):
        entry = my_books_client.add(book_id=created_book["id"]).json()

        mark_read = my_books_client.update_entry(entry["id"], status="finished")
        assert mark_read.status_code == 200

        response = my_books_client.update_entry(entry["id"], rating=5)
        assert response.status_code == 200
        body = UserBook.model_validate(response.json())
        assert body.status == "finished"
        assert body.rating == 5

    @allure.title("Нельзя поставить оценку книге, которая не 'прочитана'")
    @pytest.mark.regression
    def test_cannot_rate_unread_book(self, my_books_client, created_book):
        entry = my_books_client.add(book_id=created_book["id"], status="reading").json()

        response = my_books_client.update_entry(entry["id"], rating=5)
        assert response.status_code == 400

    @allure.title("Оценка вне диапазона 1-5 отклоняется")
    @pytest.mark.regression
    @pytest.mark.parametrize("invalid_rating", [0, 6, -1])
    def test_rating_out_of_range_rejected(self, my_books_client, created_book, invalid_rating):
        # Границы 1..5 подтверждены схемой (rating: minimum 1, maximum 5).
        entry = my_books_client.add(book_id=created_book["id"], status="finished").json()

        response = my_books_client.update_entry(entry["id"], rating=invalid_rating)
        assert response.status_code == 400

    @allure.title("Повторное добавление одной и той же книги запрещено (unique constraint)")
    @pytest.mark.regression
    def test_duplicate_entry_rejected(self, my_books_client, created_book):
        first = my_books_client.add(book_id=created_book["id"])
        assert first.status_code == 201

        second = my_books_client.add(book_id=created_book["id"])
        assert second.status_code == 400

    @allure.title("Заметки (notes) сохраняются при обновлении записи")
    @pytest.mark.regression
    def test_update_notes(self, my_books_client, created_book):
        entry = my_books_client.add(book_id=created_book["id"]).json()

        response = my_books_client.update_entry(entry["id"], notes="Перечитать вторую главу")
        assert response.status_code == 200
        assert response.json()["notes"] == "Перечитать вторую главу"

    @allure.title("started_at/finished_at сохраняются при обновлении записи")
    @pytest.mark.regression
    def test_update_reading_dates(self, my_books_client, created_book):
        entry = my_books_client.add(book_id=created_book["id"], status="reading").json()

        response = my_books_client.update_entry(entry["id"], started_at="2026-01-15")
        assert response.status_code == 200
        assert response.json()["started_at"] == "2026-01-15"

        finish_response = my_books_client.update_entry(
            entry["id"], status="finished", finished_at="2026-02-01"
        )
        assert finish_response.status_code == 200
        assert finish_response.json()["finished_at"] == "2026-02-01"

    @allure.title("Фильтр по статусу возвращает только записи этого статуса")
    @pytest.mark.regression
    def test_filter_by_status(self, my_books_client, created_book):
        my_books_client.add(book_id=created_book["id"], status="reading")

        response = my_books_client.list(status="reading")
        assert response.status_code == 200
        results = response.json()["results"] if "results" in response.json() else response.json()
        assert all(entry["status"] == "reading" for entry in results)

    @allure.title("Библиотека пользователя A недоступна пользователю B (изоляция данных)")
    @pytest.mark.regression
    def test_user_isolation(self, my_books_client, created_book, auth_client):
        my_books_client.add(book_id=created_book["id"])

        other_user = random_user()
        auth_client.register(**other_user)
        other_login = auth_client.login(other_user["username"], other_user["password"])
        other_token = other_login.json()["access"]

        from clients.my_books_client import MyBooksClient

        other_client = MyBooksClient(token=other_token)

        response = other_client.list()
        assert response.status_code == 200
        results = response.json()["results"] if "results" in response.json() else response.json()
        assert len(results) == 0

    @allure.title("Статистика библиотеки отражает добавленные книги")
    @pytest.mark.regression
    def test_stats_reflect_added_books(self, my_books_client, created_book):
        my_books_client.add(book_id=created_book["id"], status="finished", rating=4)

        response = my_books_client.stats()
        assert response.status_code == 200
        body = response.json()
        # ВНИМАНИЕ: сама OpenAPI-схема заявляет для этого эндпоинта тип
        # ответа UserBook — это явно неверно (эндпоинт возвращает
        # агрегированную статистику, не одну запись), похоже на баг
        # генерации схемы через drf-spectacular для нестандартного
        # @action. Точные поля агрегата схема не документирует, поэтому
        # здесь только проверка на непустой ответ; см. README.
        assert body

    @allure.title("Добавление несуществующей книги в библиотеку возвращает 400")
    @pytest.mark.regression
    def test_add_nonexistent_book_returns_400(self, my_books_client):
        # Стандартное поведение DRF: несуществующий pk в теле запроса
        # (PrimaryKeyRelatedField) — это ошибка валидации 400, а не 404;
        # 404 характерен для lookup по URL, не для ссылки в payload.
        response = my_books_client.add(book_id=999_999_999)
        assert response.status_code == 400

    @allure.title("Запрос без токена авторизации к my-books возвращает 401")
    @pytest.mark.regression
    def test_unauthenticated_request_rejected(self):
        from clients.my_books_client import MyBooksClient

        anonymous_client = MyBooksClient()
        response = anonymous_client.list()
        assert response.status_code == 401

    @allure.title("Недопустимое значение status при добавлении книги возвращает 400")
    @pytest.mark.regression
    def test_invalid_status_value_rejected(self, my_books_client, created_book):
        # Полный enum подтверждён реальной схемой: want_to_read/reading/
        # finished/dropped — используется заведомо невалидное значение.
        response = my_books_client.add(book_id=created_book["id"], status="not_a_real_status")
        assert response.status_code == 400
