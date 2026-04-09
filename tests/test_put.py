"""
Тесты PUT-методов API Яндекс.Диска.
"""
import uuid

import requests

from utils.disk_client import DiskApiClient


class TestCreateFolder:

    def test_create_folder_returns_201(self, client: DiskApiClient) -> None:
        path = f"pytest_put_{uuid.uuid4().hex[:8]}"
        try:
            resp = client.create_folder(path)
            assert resp.status_code == 201, f"{resp.status_code}: {resp.text}"
        finally:
            client.delete_resource(path, permanently=True)

    def test_created_folder_exists(self, client: DiskApiClient) -> None:
        path = f"pytest_put_{uuid.uuid4().hex[:8]}"
        try:
            client.create_folder(path)
            assert client.get_resource(path).status_code == 200
        finally:
            client.delete_resource(path, permanently=True)

    def test_create_folder_response_contains_href(self, client: DiskApiClient) -> None:
        path = f"pytest_put_{uuid.uuid4().hex[:8]}"
        try:
            data = client.create_folder(path).json()
            assert "href" in data, "Ответ должен содержать поле 'href'"
        finally:
            client.delete_resource(path, permanently=True)

    def test_create_existing_folder_returns_409(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        """Повторное создание уже существующей папки должно вернуть 409 Conflict."""
        response = client.create_folder(test_folder)
        assert response.status_code == 409, (
            f"Ожидался 409 Conflict, получен {response.status_code}"
        )

    def test_created_folder_type_is_dir(self, client: DiskApiClient) -> None:
        path = f"pytest_put_{uuid.uuid4().hex[:8]}"
        try:
            client.create_folder(path)
            data = client.get_resource(path).json()
            assert data["type"] == "dir"
        finally:
            client.delete_resource(path, permanently=True)


class TestUploadFile:
    """PUT <upload_url> — загрузка файла на Яндекс.Диск."""

    def test_get_upload_url_returns_200(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        response = client.get_upload_url(f"{test_folder}/any.txt")
        assert response.status_code == 200

    def test_upload_url_response_contains_href(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        data = client.get_upload_url(f"{test_folder}/any.txt").json()
        assert "href" in data, "Ответ должен содержать поле 'href'"

    def test_upload_url_is_https(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        data = client.get_upload_url(f"{test_folder}/any.txt").json()
        assert data["href"].startswith("https://"), "URL загрузки должен быть HTTPS"

    def test_upload_file_returns_201(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        file_path = f"{test_folder}/upload_test.txt"
        url_resp = client.get_upload_url(file_path, overwrite=True)
        assert url_resp.status_code == 200

        upload_url = url_resp.json()["href"]
        put_resp = requests.put(upload_url, data=b"Test content for Yandex Disk")
        assert put_resp.status_code == 201, (
            f"Ожидался 201 после загрузки, получен {put_resp.status_code}"
        )

    def test_uploaded_file_is_accessible(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        file_path = f"{test_folder}/accessible_test.txt"
        client.upload_file(file_path, b"Hello from pytest!")
        response = client.get_resource(file_path)
        assert response.status_code == 200

    def test_uploaded_file_name_is_correct(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        file_path = f"{test_folder}/named_test.txt"
        client.upload_file(file_path, b"content")
        data = client.get_resource(file_path).json()
        assert data["name"] == "named_test.txt"

    def test_overwrite_existing_file(
        self, client: DiskApiClient, test_file: str
    ) -> None:
        """Повторная загрузка с overwrite=True не должна возвращать ошибку."""
        response = client.upload_file(test_file, b"Updated content", overwrite=True)
        assert response.status_code == 201, (
            f"Ожидался 201 при перезаписи, получен {response.status_code}"
        )

    def test_upload_existing_file_without_overwrite_returns_409(
        self, client: DiskApiClient, test_file: str
    ) -> None:
        # файл уже есть, overwrite=False → должен ругнуться
        resp = client.get_upload_url(test_file, overwrite=False)
        assert resp.status_code == 409
