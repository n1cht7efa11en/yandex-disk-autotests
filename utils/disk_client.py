"""
Клиент для работы с REST API Яндекс.Диска.
Документация: https://yandex.ru/dev/disk/api/concepts/about-docpage/
"""
from __future__ import annotations

import requests

from config import BASE_URL, HEADERS


class DiskApiClient:
    """Обёртка над requests.Session для удобного обращения к API Яндекс.Диска."""

    def __init__(self, base_url: str = BASE_URL, headers: dict | None = None) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(headers or HEADERS)

    # ──────────────────────────────────────────────────────────────────────
    # GET
    # ──────────────────────────────────────────────────────────────────────

    def get_disk_info(self) -> requests.Response:
        """GET /v1/disk — общая информация о диске пользователя."""
        return self.session.get(self.base_url)

    def get_resource(self, path: str, **params) -> requests.Response:
        """GET /v1/disk/resources — метаинформация о файле или папке."""
        return self.session.get(
            f"{self.base_url}/resources",
            params={"path": path, **params},
        )

    def get_flat_list(self, limit: int = 20, **params) -> requests.Response:
        """GET /v1/disk/resources/files — плоский список всех файлов на диске."""
        return self.session.get(
            f"{self.base_url}/resources/files",
            params={"limit": limit, **params},
        )

    def get_upload_url(self, path: str, overwrite: bool = False) -> requests.Response:
        """GET /v1/disk/resources/upload — получить URL для загрузки файла."""
        return self.session.get(
            f"{self.base_url}/resources/upload",
            params={"path": path, "overwrite": str(overwrite).lower()},
        )

    def get_download_url(self, path: str) -> requests.Response:
        """GET /v1/disk/resources/download — получить URL для скачивания файла."""
        return self.session.get(
            f"{self.base_url}/resources/download",
            params={"path": path},
        )

    def download_file(self, path: str) -> requests.Response:
        """
        Скачать файл с Диска.

        Шаг 1: GET /v1/disk/resources/download — получить URL.
        Шаг 2: GET <url> — скачать содержимое.

        Возвращает ответ с содержимым файла.
        """
        url_response = self.get_download_url(path)
        if url_response.status_code != 200:
            return url_response
        download_url: str = url_response.json()["href"]
        return requests.get(download_url)

    def get_operation_status(self, operation_id: str) -> requests.Response:
        """GET /v1/disk/operations — статус асинхронной операции."""
        return self.session.get(
            f"{self.base_url}/operations",
            params={"id": operation_id},
        )

    def get_trash_resources(self, **params) -> requests.Response:
        """GET /v1/disk/trash/resources — содержимое корзины."""
        return self.session.get(f"{self.base_url}/trash/resources", params=params)

    # ──────────────────────────────────────────────────────────────────────
    # TRASH
    # ──────────────────────────────────────────────────────────────────────

    def restore_from_trash(self, path: str, overwrite: bool = False) -> requests.Response:
        """PUT /v1/disk/trash/resources/restore — восстановить ресурс из корзины."""
        return self.session.put(
            f"{self.base_url}/trash/resources/restore",
            params={"path": path, "overwrite": str(overwrite).lower()},
        )

    def clear_trash(self, path: str | None = None) -> requests.Response:
        """
        DELETE /v1/disk/trash/resources — очистить корзину или удалить элемент из неё.

        path=None — очистить всю корзину.
        path=<trash_path> — удалить конкретный элемент.
        """
        params = {"path": path} if path else {}
        return self.session.delete(f"{self.base_url}/trash/resources", params=params)

    # ──────────────────────────────────────────────────────────────────────
    # PUT
    # ──────────────────────────────────────────────────────────────────────

    def create_folder(self, path: str) -> requests.Response:
        """PUT /v1/disk/resources — создать папку по указанному пути."""
        return self.session.put(
            f"{self.base_url}/resources",
            params={"path": path},
        )

    def upload_file(self, path: str, data: bytes, overwrite: bool = True) -> requests.Response:
        """
        Загрузить файл на Диск.

        Шаг 1: GET /v1/disk/resources/upload — получить URL.
        Шаг 2: PUT <url> — передать содержимое файла.

        Возвращает ответ PUT-запроса (201 Created при успехе).
        """
        url_response = self.get_upload_url(path, overwrite=overwrite)
        if url_response.status_code != 200:
            return url_response
        upload_url: str = url_response.json()["href"]
        return requests.put(upload_url, data=data)

    # ──────────────────────────────────────────────────────────────────────
    # POST
    # ──────────────────────────────────────────────────────────────────────

    def copy_resource(
        self, from_path: str, to_path: str, overwrite: bool = False
    ) -> requests.Response:
        """POST /v1/disk/resources/copy — скопировать ресурс."""
        return self.session.post(
            f"{self.base_url}/resources/copy",
            params={"from": from_path, "path": to_path, "overwrite": str(overwrite).lower()},
        )

    def move_resource(
        self, from_path: str, to_path: str, overwrite: bool = False
    ) -> requests.Response:
        """POST /v1/disk/resources/move — переместить / переименовать ресурс."""
        return self.session.post(
            f"{self.base_url}/resources/move",
            params={"from": from_path, "path": to_path, "overwrite": str(overwrite).lower()},
        )

    # ──────────────────────────────────────────────────────────────────────
    # DELETE
    # ──────────────────────────────────────────────────────────────────────

    def delete_resource(self, path: str, permanently: bool = False) -> requests.Response:
        """
        DELETE /v1/disk/resources — удалить ресурс.

        permanently=True  — удалить без корзины.
        permanently=False — переместить в корзину (по умолчанию).
        """
        return self.session.delete(
            f"{self.base_url}/resources",
            params={"path": path, "permanently": str(permanently).lower()},
        )
