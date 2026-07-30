import allure
import pytest

from schemas.models import PaginatedBooks

PAGE_SIZE = 20  # заявлено в README проекта; см. TODO ниже


@allure.epic("Book Tracker API")
@allure.feature("Пагинация")
class TestPagination:
    @allure.title("Первая страница содержит не больше PAGE_SIZE записей и ссылку next")
    @pytest.mark.regression
    def test_first_page_has_next_link(self, books_client, many_books):
        # TODO: PAGE_SIZE подсмотрен в README ("по 20 записей"), не сверен
        # напрямую с настройками пагинатора DRF — если он другой, поправить
        # константу и число создаваемых книг ниже.
        many_books(PAGE_SIZE + 5)
        prefix = many_books.prefix

        response = books_client.list(search=prefix, page=1)
        assert response.status_code == 200
        body = PaginatedBooks.model_validate(response.json())

        assert len(body.results) <= PAGE_SIZE
        assert body.next is not None
        assert body.previous is None

    @allure.title("Последняя страница не содержит ссылку next")
    @pytest.mark.regression
    def test_last_page_has_no_next_link(self, books_client, many_books):
        many_books(PAGE_SIZE + 5)
        prefix = many_books.prefix

        response = books_client.list(search=prefix, page=2)
        assert response.status_code == 200
        body = PaginatedBooks.model_validate(response.json())

        assert body.previous is not None
        assert body.next is None

    @allure.title("count в ответе соответствует реальному числу объектов на всех страницах")
    @pytest.mark.regression
    def test_count_matches_total_across_pages(self, books_client, many_books):
        total_created = PAGE_SIZE + 5
        many_books(total_created)
        prefix = many_books.prefix

        first_page = books_client.list(search=prefix, page=1).json()
        second_page = books_client.list(search=prefix, page=2).json()

        assert first_page["count"] == total_created
        assert len(first_page["results"]) + len(second_page["results"]) == total_created
