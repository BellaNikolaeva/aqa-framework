import json
from pathlib import Path

import pytest

from clients.auth_client import AuthClient
from clients.books_client import BooksClient
from clients.my_books_client import MyBooksClient
from clients.tags_client import TagsClient
from utils.data_generator import random_user

# --- Видимость flaky-тестов -------------------------------------------------
# pytest-rerunfailures сам по себе просто тихо перезапускает упавший тест —
# итоговый прогон становится зелёным, и никто не узнаёт, что конкретный тест
# на самом деле нестабилен. Здесь явно собираем список тестов, прошедших
# только со второй попытки, печатаем его в конце прогона и пишем в файл,
# чтобы CI мог поднять это как отдельный сигнал, а не спрятать в статистике.
_flaky_tests: list[str] = []


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if getattr(report, "outcome", None) == "rerun" and report.nodeid not in _flaky_tests:
        _flaky_tests.append(report.nodeid)


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    report_path = Path("flaky-tests.json")
    report_path.write_text(json.dumps({"flaky_tests": _flaky_tests}, ensure_ascii=False, indent=2))

    if not _flaky_tests:
        return

    terminalreporter.write_sep("=", "FLAKY: прошли только после перезапуска", red=True, bold=True)
    for nodeid in _flaky_tests:
        terminalreporter.write_line(f"  ⚠️  {nodeid}")
    terminalreporter.write_line(f"Полный список — {report_path}")


# -----------------------------------------------------------------------------


@pytest.fixture
def auth_client():
    return AuthClient()


@pytest.fixture
def registered_user(auth_client):
    """Регистрирует нового случайного пользователя и возвращает его данные."""
    user_data = random_user()
    response = auth_client.register(**user_data)
    assert response.status_code == 201, f"Регистрация не удалась: {response.text}"
    return user_data


@pytest.fixture
def auth_token(auth_client, registered_user):
    response = auth_client.login(registered_user["username"], registered_user["password"])
    assert response.status_code == 200, f"Логин не удался: {response.text}"
    return response.json()["access"]


@pytest.fixture
def books_client(auth_token):
    return BooksClient(token=auth_token)


@pytest.fixture
def my_books_client(auth_token):
    return MyBooksClient(token=auth_token)


@pytest.fixture
def tags_client(auth_token):
    return TagsClient(token=auth_token)


@pytest.fixture
def created_book(books_client):
    """Создаёт книгу и удаляет её после теста (teardown), не оставляя мусор в БД."""
    from utils.data_generator import random_book

    response = books_client.create(**random_book())
    assert response.status_code == 201, f"Создание книги не удалось: {response.text}"
    book = response.json()

    yield book

    books_client.delete_book(book["id"])


@pytest.fixture
def many_books(books_client):
    """
    Создаёт заданное число книг с уникальным префиксом в названии для
    проверки пагинации, удаляет все после теста. Префикс нужен, чтобы
    тест не зависел от состояния общего каталога (он не привязан к
    пользователю — см. README) и был безопасен при параллельном прогоне.
    """
    from utils.data_generator import random_book, random_tag_name

    prefix = random_tag_name()  # достаточно уникальный короткий токен

    def _create(count: int):
        created = []
        for _ in range(count):
            payload = random_book()
            payload["title"] = f"{prefix} {payload['title']}"
            created.append(books_client.create(**payload).json())
        _create.ids = [book["id"] for book in created]
        return created

    _create.prefix = prefix
    yield _create

    for book_id in getattr(_create, "ids", []):
        books_client.delete_book(book_id)
