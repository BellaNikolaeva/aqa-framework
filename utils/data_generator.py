"""
Генерация случайных тестовых данных, чтобы тесты не конфликтовали
друг с другом при параллельном запуске и не зависели от фикстур в БД.
"""

import random

from faker import Faker

fake = Faker("ru_RU")


def random_user() -> dict:
    unique = fake.uuid4()[:8]
    return {
        "username": f"aqa_{unique}",
        "email": f"aqa_{unique}@example.com",
        "password": "StrongPass123!",
    }


def random_book() -> dict:
    # genre — обычная строка (maxLength: 100), не enum: подтверждено
    # реальной OpenAPI-схемой (Book_Tracker_API.yaml), значения ниже
    # просто правдоподобные примеры, а не проверка по списку допустимых.
    return {
        "title": fake.sentence(nb_words=3).rstrip("."),
        "author": fake.name(),
        "genre": random.choice(["fantasy", "detective", "classic", "sci_fi", "non_fiction"]),
        "year_published": random.randint(1950, 2026),
        "cover_url": fake.image_url(),
    }


def random_tag_name() -> str:
    # Без общего литерального префикса вроде "tag-": если поиск на
    # бэкенде токенизированный (full-text), а не точный icontains, общий
    # префикс у всех сгенерированных тегов даёт ложные совпадения между
    # заведомо разными тегами — нашли это на реальном API.
    return f"{fake.word()}-{fake.uuid4()}"


def random_unique_token() -> str:
    """UUID, гарантированно не встречающийся ни в каких существующих
    данных — для тестов поиска/фильтрации, независимых от реального
    состояния общего каталога и точной семантики поиска на бэкенде."""
    return str(fake.uuid4())
