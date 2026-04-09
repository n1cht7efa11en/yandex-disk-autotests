"""
Тесты DELETE-методов API Яндекс.Диска.
"""
import uuid

from utils.disk_client import DiskApiClient


class TestDeleteResource:

    def test_delete_folder_permanently_returns_204(
        self, client: DiskApiClient
    ) -> None:
        path = f"pytest_del_{uuid.uuid4().hex[:8]}"
        client.create_folder(path)
        resp = client.delete_resource(path, permanently=True)
        assert resp.status_code == 204, f"получен {resp.status_code}: {resp.text}"

    def test_deleted_folder_is_not_accessible(self, client: DiskApiClient) -> None:
        path = f"pytest_del_{uuid.uuid4().hex[:8]}"
        client.create_folder(path)
        client.delete_resource(path, permanently=True)
        assert client.get_resource(path).status_code == 404

    def test_delete_nonexistent_resource_returns_404(
        self, client: DiskApiClient
    ) -> None:
        response = client.delete_resource(
            "nonexistent_xyz_99999", permanently=True
        )
        assert response.status_code == 404

    def test_delete_file_returns_204(
        self, client: DiskApiClient, test_file: str
    ) -> None:
        response = client.delete_resource(test_file, permanently=True)
        assert response.status_code == 204

    def test_deleted_file_returns_404_on_get(
        self, client: DiskApiClient, test_file: str
    ) -> None:
        client.delete_resource(test_file, permanently=True)
        response = client.get_resource(test_file)
        assert response.status_code == 404

    def test_soft_delete_returns_202_or_204(self, client: DiskApiClient) -> None:
        # permanently=False → файл идёт в корзину, не удаляется насовсем
        path = f"pytest_trash_{uuid.uuid4().hex[:8]}"
        client.create_folder(path)
        response = client.delete_resource(path, permanently=False)
        assert response.status_code in (202, 204), (
            f"Ожидался 202 или 204, получен {response.status_code}: {response.text}"
        )
        # Очищаем корзину от тестового ресурса, если он там оказался
        client.delete_resource(f"trash:/{path}", permanently=True)

    def test_soft_deleted_file_appears_in_trash(
        self, client: DiskApiClient
    ) -> None:
        path = f"pytest_trash_check_{uuid.uuid4().hex[:8]}"
        client.create_folder(path)
        client.delete_resource(path, permanently=False)

        try:
            trash_resp = client.get_trash_resources()
            assert trash_resp.status_code == 200, (
                f"Не удалось получить содержимое корзины: {trash_resp.status_code}"
            )
            items = trash_resp.json().get("_embedded", {}).get("items", [])
            trash_names = [item["name"] for item in items]
            assert path in trash_names, (
                f"Папка '{path}' не найдена в корзине. Элементы корзины: {trash_names}"
            )
        finally:
            client.delete_resource(f"trash:/{path}", permanently=True)

    def test_delete_folder_with_contents(
        self, client: DiskApiClient, test_file: str, test_folder: str
    ) -> None:
        """Непустая папка: 202 (async) или 204."""
        resp = client.delete_resource(test_folder, permanently=True)
        assert resp.status_code in (202, 204)
