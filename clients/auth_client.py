from clients.base_client import BaseClient


class AuthClient(BaseClient):
    def register(self, **fields):
        # Специально без обязательных позиционных аргументов: негативные тесты
        # должны иметь возможность отправить запрос с отсутствующим полем
        # и проверить, что именно API возвращает 400, а не что упадёт клиент.
        return self.post("/api/auth/register/", json=fields)

    def login(self, username: str, password: str):
        return self.post("/api/auth/login/", json={"username": username, "password": password})

    def refresh(self, refresh_token: str):
        return self.post("/api/auth/refresh/", json={"refresh": refresh_token})
