"""
Тесты корзины Яндекс.Диска (trash).
"""
import uuid

import pytest

from utils.disk_client import DiskApiClient


class TestSoftDelete:

    def test_soft_delete_returns_202_or_204(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        file_path = f"{test_folder}/soft_delete_test.txt"
        client.upload_file(file_path, b"soft delete content")
        resp = client.delete_resource(file_path, permanently=False)
        assert resp.status_code in (202, 204)

    def test_soft_deleted_file_not_accessible_at_original_path(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        file_path = f"{test_folder}/gone_after_trash.txt"
        client.upload_file(file_path, b"data")
        client.delete_resource(file_path, permanently=False)

        # файл ушёл в корзину — по исходному пути его быть не должно
        assert client.get_resource(file_path).status_code == 404

    def test_soft_deleted_file_appears_in_trash(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        unique_name = f"trash_check_{uuid.uuid4().hex[:8]}.txt"
        file_path = f"{test_folder}/{unique_name}"
        client.upload_file(file_path, b"trash content")
        client.delete_resource(file_path, permanently=False)

        items = client.get_trash_resources().json().get("_embedded", {}).get("items", [])
        names = [i["name"] for i in items]
        assert unique_name in names, f"'{unique_name}' не найден в корзине: {names}"


class TestTrashRestore:

    def test_restore_returns_201_or_202(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        unique_name = f"restore_test_{uuid.uuid4().hex[:8]}.txt"
        file_path = f"{test_folder}/{unique_name}"
        client.upload_file(file_path, b"restore me")
        client.delete_resource(file_path, permanently=False)

        items = client.get_trash_resources().json().get("_embedded", {}).get("items", [])
        trash_item = next((i for i in items if i["name"] == unique_name), None)
        assert trash_item is not None, "Файл не найден в корзине"

        resp = client.restore_from_trash(trash_item["path"])
        assert resp.status_code in (201, 202)

    def test_restored_file_accessible_at_original_path(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        unique_name = f"restore_access_{uuid.uuid4().hex[:8]}.txt"
        file_path = f"{test_folder}/{unique_name}"
        client.upload_file(file_path, b"restore content")
        client.delete_resource(file_path, permanently=False)

        items = client.get_trash_resources().json().get("_embedded", {}).get("items", [])
        trash_item = next((i for i in items if i["name"] == unique_name), None)
        assert trash_item is not None

        client.restore_from_trash(trash_item["path"])
        assert client.get_resource(file_path).status_code == 200

    def test_restore_nonexistent_trash_item_returns_404(
        self, client: DiskApiClient
    ) -> None:
        resp = client.restore_from_trash("trash:/nonexistent_xyz_99999.txt")
        assert resp.status_code == 404


class TestClearTrash:

    def test_delete_specific_item_from_trash(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        unique_name = f"perm_delete_{uuid.uuid4().hex[:8]}.txt"
        file_path = f"{test_folder}/{unique_name}"
        client.upload_file(file_path, b"permanent trash delete")
        client.delete_resource(file_path, permanently=False)

        items = client.get_trash_resources().json().get("_embedded", {}).get("items", [])
        trash_item = next((i for i in items if i["name"] == unique_name), None)
        assert trash_item is not None

        resp = client.clear_trash(path=trash_item["path"])
        assert resp.status_code in (202, 204)

    def test_item_not_in_trash_after_permanent_delete(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        unique_name = f"gone_from_trash_{uuid.uuid4().hex[:8]}.txt"
        file_path = f"{test_folder}/{unique_name}"
        client.upload_file(file_path, b"data")
        client.delete_resource(file_path, permanently=False)

        items = client.get_trash_resources().json().get("_embedded", {}).get("items", [])
        trash_item = next((i for i in items if i["name"] == unique_name), None)
        assert trash_item is not None

        client.clear_trash(path=trash_item["path"])

        items_after = client.get_trash_resources().json().get("_embedded", {}).get("items", [])
        assert unique_name not in [i["name"] for i in items_after]

    def test_clear_entire_trash_returns_202_or_204(
        self, client: DiskApiClient
    ) -> None:
        resp = client.clear_trash()
        assert resp.status_code in (202, 204)
