"""
Pydantic-модели ожидаемого контракта ответов API — сверены построчно
с реальной OpenAPI-схемой (Book_Tracker_API.yaml), а не с догадками.

В отличие от голых JSON Schema, модель одновременно и валидирует
ответ, и даёт типизированный объект для дальнейших проверок в тесте
(book.title вместо book["title"] с риском KeyError).
"""

from pydantic import BaseModel, ConfigDict


class Tag(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class Book(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    title: str
    author: str
    # genre — обычная строка (maxLength: 100), НЕ enum и НЕ обязательное
    # поле: в схеме required для Book — только author/created_at/id/tags/title.
    genre: str = ""
    year_published: int | None = None
    # cover_url — по схеме либо валидный URI, либо пустая строка (не null).
    cover_url: str = ""
    tags: list[Tag] = []
    created_at: str | None = None


class PaginatedBooks(BaseModel):
    model_config = ConfigDict(extra="allow")

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[Book]


class PaginatedTags(BaseModel):
    model_config = ConfigDict(extra="allow")

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[Tag]


class UserBook(BaseModel):
    """
    Запись личной библиотеки. ВАЖНО: в ответе (GET/POST/PATCH) приходит
    вложенный объект `book`, а не `book_id` — `book_id` в схеме помечен
    writeOnly и существует только в теле запроса. Изначальная версия этой
    модели ошибочно требовала book_id в ответе; исправлено по реальной схеме.
    """

    model_config = ConfigDict(extra="allow")

    id: int
    book: Book
    status: str
    rating: int | None = None
    notes: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None


class PaginatedUserBooks(BaseModel):
    model_config = ConfigDict(extra="allow")

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[UserBook]
