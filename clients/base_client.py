"""
Базовый HTTP-клиент. Все клиенты конкретных ресурсов (Auth, Books, ...)
наследуются от него, чтобы не дублировать логику логирования,
подстановки токена, ретраев и обработки ответа.
"""

import json
import logging

import allure
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from config.settings import DEFAULT_HEADERS, settings

logger = logging.getLogger("aqa.client")

RETRYABLE_STATUS_CODES = {502, 503, 504}


class RetryableStatusError(Exception):
    """Внутреннее исключение, чтобы tenacity могла ретраить 5xx так же,
    как обрывы соединения — оба сценария типичны для "спящего" Render."""


class BaseClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = str(base_url or settings.base_url).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self) -> None:
        self.session.headers.pop("Authorization", None)

    @retry(
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, RetryableStatusError)),
        stop=stop_after_attempt(settings.retry_attempts),
        wait=wait_fixed(settings.retry_wait_seconds),
        reraise=True,
    )
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", settings.timeout)

        logger.info("%s %s | payload=%s", method, url, kwargs.get("json"))
        response = self.session.request(method, url, **kwargs)
        logger.info("-> %s in %.2fs", response.status_code, response.elapsed.total_seconds())

        self._attach_to_allure(method, url, kwargs.get("json"), response)

        if response.status_code in RETRYABLE_STATUS_CODES:
            raise RetryableStatusError(f"{response.status_code} from {url}")
        return response

    @staticmethod
    def _attach_to_allure(method: str, url: str, payload: dict | None, response: requests.Response) -> None:
        body = {
            "request": {"method": method, "url": url, "payload": payload},
            "response": {
                "status_code": response.status_code,
                "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 1),
                "body": _safe_json(response),
            },
        }
        allure.attach(
            json.dumps(body, ensure_ascii=False, indent=2),
            name=f"{method} {url}",
            attachment_type=allure.attachment_type.JSON,
        )

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: dict | None = None, **kwargs) -> requests.Response:
        return self._request("POST", path, json=json, **kwargs)

    def patch(self, path: str, json: dict | None = None, **kwargs) -> requests.Response:
        return self._request("PATCH", path, json=json, **kwargs)

    def put(self, path: str, json: dict | None = None, **kwargs) -> requests.Response:
        return self._request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request("DELETE", path, **kwargs)


def _safe_json(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return response.text
