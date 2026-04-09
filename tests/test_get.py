"""
Тесты GET-методов API Яндекс.Диска.
"""

import pytest

from utils.disk_client import DiskApiClient


class TestGetDiskInfo:

    def test_status_code_200(self, client: DiskApiClient) -> None:
        resp = client.get_disk_info()
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text}"

    def test_response_is_json(self, client: DiskApiClient) -> None:
        response = client.get_disk_info()
        assert "application/json" in response.headers.get("Content-Type", "")

    def test_response_contains_total_space(self, client: DiskApiClient) -> None:
        data = client.get_disk_info().json()
        assert "total_space" in data

    def test_response_contains_used_space(self, client: DiskApiClient) -> None:
        data = client.get_disk_info().json()
        assert "used_space" in data, "Поле 'used_space' отсутствует в ответе"

    def test_total_space_is_positive(self, client: DiskApiClient) -> None:
        data = client.get_disk_info().json()
        assert data["total_space"] > 0

    def test_used_space_not_exceeds_total(self, client: DiskApiClient) -> None:
        data = client.get_disk_info().json()
        assert data["used_space"] <= data["total_space"]


class TestGetResource:

    def test_get_existing_folder_returns_200(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        assert client.get_resource(test_folder).status_code == 200

    def test_response_contains_name(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        data = client.get_resource(test_folder).json()
        assert "name" in data

    def test_folder_name_matches_requested(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        data = client.get_resource(test_folder).json()
        assert data["name"] == test_folder

    def test_folder_type_is_dir(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        data = client.get_resource(test_folder).json()
        assert data["type"] == "dir", f"Ожидался 'dir', получен '{data['type']}'"

    def test_get_nonexistent_resource_returns_404(
        self, client: DiskApiClient
    ) -> None:
        response = client.get_resource("nonexistent_resource_xyz_99999")
        assert response.status_code == 404

    def test_file_type_is_file(
        self, client: DiskApiClient, test_file: str
    ) -> None:
        meta = client.get_resource(test_file).json()
        assert meta["type"] == "file"

    def test_response_contains_path(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        data = client.get_resource(test_folder).json()
        assert "path" in data


class TestGetFlatList:
    """GET /v1/disk/resources/files."""

    def test_status_code_200(self, client: DiskApiClient) -> None:
        assert client.get_flat_list().status_code == 200

    def test_response_contains_items(self, client: DiskApiClient) -> None:
        data = client.get_flat_list().json()
        assert "items" in data

    def test_items_count_respects_limit(self, client: DiskApiClient) -> None:
        limit = 5
        items = client.get_flat_list(limit=limit).json()["items"]
        assert len(items) <= limit

    def test_response_contains_limit_field(self, client: DiskApiClient) -> None:
        data = client.get_flat_list().json()
        assert "limit" in data

    def test_items_is_list(self, client: DiskApiClient) -> None:
        data = client.get_flat_list().json()
        assert isinstance(data["items"], list)
