"""
Security-смоук: не полноценный пентест, а быстрый набор проверок на
самые типичные и дешёвые в эксплуатации уязвимости API — сломанная
аутентификация, IDOR, инъекции в поисковые параметры. Дополняет
функциональные тесты, а не заменяет их.
"""

import allure
import pytest

from clients.books_client import BooksClient
from clients.my_books_client import MyBooksClient
from utils.data_generator import random_book, random_user


@allure.epic("Book Tracker API")
@allure.feature("Безопасность")
class TestAuthSecurity:
    @allure.title("Синтаксически некорректный токен отклоняется")
    @pytest.mark.smoke
    def test_malformed_token_rejected(self):
        client = BooksClient(token="not-a-jwt-at-all")
        response = client.create(**random_book())
        assert response.status_code == 401

    @allure.title("Токен с изменённой подписью (tampered JWT) отклоняется")
    @pytest.mark.smoke
    def test_tampered_token_signature_rejected(self, auth_client, registered_user):
        login = auth_client.login(registered_user["username"], registered_user["password"])
        token = login.json()["access"]

        # Портим последний символ подписи — структура JWT (header.payload.signature)
        # остаётся правдоподобной, но подпись больше не совпадает с секретом сервера.
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

        client = BooksClient(token=tampered)
        response = client.create(**random_book())
        assert response.status_code == 401

    @allure.title("Неверная auth-схема (не Bearer) отклоняется")
    @pytest.mark.regression
    def test_wrong_auth_scheme_rejected(self, auth_client, registered_user):
        login = auth_client.login(registered_user["username"], registered_user["password"])
        token = login.json()["access"]

        client = BooksClient()
        client.session.headers["Authorization"] = f"Token {token}"  # не Bearer
        response = client.create(**random_book())
        assert response.status_code == 401

    @allure.title("Пустой токен (Bearer без значения) отклоняется")
    @pytest.mark.regression
    def test_empty_bearer_token_rejected(self):
        client = BooksClient()
        client.session.headers["Authorization"] = "Bearer "
        response = client.create(**random_book())
        assert response.status_code == 401

    # Полноценный тест на просроченный токен здесь невозможен: без
    # секрета подписи сервера нельзя сгенерировать валидно подписанный,
    # но именно просроченный JWT — только реальный сервер решает,
    # истёк токен или нет. Синтетически подделанный "expired-looking"
    # токен неотличим от tampered-теста выше по сути проверки.


@allure.epic("Book Tracker API")
@allure.feature("Безопасность")
class TestIDOR:
    @allure.title("Прямой доступ к чужой записи my-books по id возвращает 404, не 403")
    @pytest.mark.smoke
    def test_cannot_access_other_users_my_book_entry_directly(
        self, my_books_client, created_book, auth_client
    ):
        # 404, а не 403 — принципиально: 403 подтвердил бы факт существования
        # записи с этим id у другого пользователя (утечка информации),
        # 404 не раскрывает вообще ничего.
        entry = my_books_client.add(book_id=created_book["id"]).json()

        other_user = random_user()
        auth_client.register(**other_user)
        other_login = auth_client.login(other_user["username"], other_user["password"])
        other_client = MyBooksClient(token=other_login.json()["access"])

        response = other_client.get_by_id(entry["id"])
        assert response.status_code == 404

    @allure.title("Чужую запись my-books нельзя изменить по id")
    @pytest.mark.regression
    def test_cannot_update_other_users_my_book_entry(self, my_books_client, created_book, auth_client):
        entry = my_books_client.add(book_id=created_book["id"]).json()

        other_user = random_user()
        auth_client.register(**other_user)
        other_login = auth_client.login(other_user["username"], other_user["password"])
        other_client = MyBooksClient(token=other_login.json()["access"])

        response = other_client.update_entry(entry["id"], status="dropped")
        assert response.status_code == 404

    @allure.title("Чужую запись my-books нельзя удалить по id")
    @pytest.mark.regression
    def test_cannot_delete_other_users_my_book_entry(self, my_books_client, created_book, auth_client):
        entry = my_books_client.add(book_id=created_book["id"]).json()

        other_user = random_user()
        auth_client.register(**other_user)
        other_login = auth_client.login(other_user["username"], other_user["password"])
        other_client = MyBooksClient(token=other_login.json()["access"])

        response = other_client.remove(entry["id"])
        assert response.status_code == 404

        # запись должна остаться нетронутой у настоящего владельца
        still_there = my_books_client.get_by_id(entry["id"])
        assert still_there.status_code == 200


@allure.epic("Book Tracker API")
@allure.feature("Безопасность")
class TestInjectionAttempts:
    @allure.title("SQL-инъекция в поиске книг не роняет сервер и не даёт лишних данных")
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "payload",
        [
            "' OR '1'='1",
            "'; DROP TABLE books;--",
            '" OR ""="',
        ],
    )
    def test_sql_injection_in_book_search(self, books_client, payload):
        response = books_client.search(query=payload)
        # Главная проверка — сервер не падает (не 500) и не исполняет
        # инъекцию. 200 (запрос обработан как обычный текст, ORM
        # параметризует запросы сам) и 403 (запрос заблокирован на каком-то
        # промежуточном уровне — например, WAF или защита хостинга по
        # сигнатурам вроде "DROP TABLE") — оба безопасные исходы. Только
        # 500 значил бы, что инъекция реально задела бэкенд.
        assert response.status_code in (200, 403), f"Неожиданный статус: {response.status_code}"
        if response.status_code == 200:
            assert "results" in response.json()

    @allure.title("SQL-инъекция в поиске тегов не роняет сервер")
    @pytest.mark.regression
    def test_sql_injection_in_tag_search(self, tags_client):
        response = tags_client.list(search="'; DROP TABLE tags;--")
        assert response.status_code in (200, 403), f"Неожиданный статус: {response.status_code}"
        if response.status_code == 200:
            assert "results" in response.json()

    @allure.title("XSS-пейлоад в названии книги сохраняется как обычный текст, не исполняется")
    @pytest.mark.regression
    def test_xss_payload_stored_as_plain_text(self, books_client):
        payload = "<script>alert('xss')</script>"
        response = books_client.create(title=payload, author="Test Author", genre="test")
        assert response.status_code == 201
        # API — не то место, где XSS может исполниться (это забота фронта),
        # но важно, что бэкенд возвращает данные как есть, без серверных
        # 500-к на спецсимволы и без попытки их выполнить/проглотить молча.
        assert response.json()["title"] == payload

        books_client.delete_book(response.json()["id"])
