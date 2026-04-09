"""
Тесты POST-методов API Яндекс.Диска.
"""
import uuid

from utils.disk_client import DiskApiClient


class TestCopyResource:
    """POST /v1/disk/resources/copy — копирование ресурса."""

    def test_copy_folder_returns_201_or_202(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        """201 — синхронная копия, 202 — асинхронная (для больших объектов)."""
        copy_path = f"{test_folder}_copy_{uuid.uuid4().hex[:6]}"
        try:
            response = client.copy_resource(test_folder, copy_path)
            assert response.status_code in (201, 202), (
                f"Ожидался 201 или 202, получен {response.status_code}: {response.text}"
            )
        finally:
            client.delete_resource(copy_path, permanently=True)

    def test_copied_resource_exists(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        copy_path = f"{test_folder}_copy_{uuid.uuid4().hex[:6]}"
        try:
            client.copy_resource(test_folder, copy_path)
            response = client.get_resource(copy_path)
            assert response.status_code == 200, (
                "Скопированный ресурс должен быть доступен"
            )
        finally:
            client.delete_resource(copy_path, permanently=True)

    def test_original_resource_still_exists_after_copy(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        copy_path = f"{test_folder}_copy_{uuid.uuid4().hex[:6]}"
        try:
            client.copy_resource(test_folder, copy_path)
            response = client.get_resource(test_folder)
            assert response.status_code == 200, (
                "Исходный ресурс должен сохраниться после копирования"
            )
        finally:
            client.delete_resource(copy_path, permanently=True)

    def test_copy_nonexistent_resource_returns_404(
        self, client: DiskApiClient
    ) -> None:
        response = client.copy_resource(
            "nonexistent_src_xyz_99999", "copy_dst_xyz_99999"
        )
        assert response.status_code == 404

    def test_copy_to_existing_destination_without_overwrite_returns_409(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        src = f"{test_folder}_conflict_src_{uuid.uuid4().hex[:6]}"
        client.create_folder(src)
        try:
            resp = client.copy_resource(src, test_folder, overwrite=False)
            assert resp.status_code == 409
        finally:
            client.delete_resource(src, permanently=True)

    def test_copy_to_existing_destination_with_overwrite_succeeds(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        """overwrite=True — должно пройти без ошибки."""
        src = f"{test_folder}_overwrite_src_{uuid.uuid4().hex[:6]}"
        client.create_folder(src)
        try:
            resp = client.copy_resource(src, test_folder, overwrite=True)
            assert resp.status_code in (201, 202)
        finally:
            client.delete_resource(src, permanently=True)

    def test_copy_file(
        self, client: DiskApiClient, test_file: str, test_folder: str
    ) -> None:
        copy_path = f"{test_folder}/copied_file.txt"
        try:
            response = client.copy_resource(test_file, copy_path)
            assert response.status_code in (201, 202)
        finally:
            client.delete_resource(copy_path, permanently=True)


class TestMoveResource:
    """POST /v1/disk/resources/move — перемещение / переименование ресурса."""

    def test_move_folder_returns_201_or_202(self, client: DiskApiClient) -> None:
        src = f"pytest_move_src_{uuid.uuid4().hex[:8]}"
        dst = f"pytest_move_dst_{uuid.uuid4().hex[:8]}"
        client.create_folder(src)
        try:
            response = client.move_resource(src, dst)
            assert response.status_code in (201, 202), (
                f"Ожидался 201 или 202, получен {response.status_code}: {response.text}"
            )
        finally:
            client.delete_resource(src, permanently=True)
            client.delete_resource(dst, permanently=True)

    def test_source_disappears_after_move(self, client: DiskApiClient) -> None:
        src = f"pytest_move_src_{uuid.uuid4().hex[:8]}"
        dst = f"pytest_move_dst_{uuid.uuid4().hex[:8]}"
        client.create_folder(src)
        try:
            client.move_resource(src, dst)
            assert client.get_resource(src).status_code == 404, (
                "Источник должен исчезнуть после перемещения"
            )
        finally:
            client.delete_resource(src, permanently=True)
            client.delete_resource(dst, permanently=True)

    def test_destination_exists_after_move(self, client: DiskApiClient) -> None:
        src = f"pytest_move_src_{uuid.uuid4().hex[:8]}"
        dst = f"pytest_move_dst_{uuid.uuid4().hex[:8]}"
        client.create_folder(src)
        try:
            client.move_resource(src, dst)
            assert client.get_resource(dst).status_code == 200, (
                "Ресурс должен быть доступен по новому пути"
            )
        finally:
            client.delete_resource(src, permanently=True)
            client.delete_resource(dst, permanently=True)

    def test_rename_folder(self, client: DiskApiClient) -> None:
        """Перемещение в тот же каталог — фактически переименование."""
        src = f"pytest_rename_src_{uuid.uuid4().hex[:8]}"
        dst = f"pytest_rename_dst_{uuid.uuid4().hex[:8]}"
        client.create_folder(src)
        try:
            response = client.move_resource(src, dst)
            assert response.status_code in (201, 202)
            data = client.get_resource(dst).json()
            assert data["name"] == dst
        finally:
            client.delete_resource(src, permanently=True)
            client.delete_resource(dst, permanently=True)

    def test_move_to_existing_destination_without_overwrite_returns_409(
        self, client: DiskApiClient
    ) -> None:
        src = f"pytest_move_conflict_src_{uuid.uuid4().hex[:8]}"
        dst = f"pytest_move_conflict_dst_{uuid.uuid4().hex[:8]}"
        client.create_folder(src)
        client.create_folder(dst)
        try:
            resp = client.move_resource(src, dst, overwrite=False)
            assert resp.status_code == 409, f"получен {resp.status_code}"
        finally:
            client.delete_resource(src, permanently=True)
            client.delete_resource(dst, permanently=True)

    def test_metadata_path_updated_after_move(
        self, client: DiskApiClient
    ) -> None:
        """
        После перемещения поле 'path' в метаданных ресурса должно
        отражать новое местоположение, а не старое.
        """
        src = f"pytest_meta_src_{uuid.uuid4().hex[:8]}"
        dst = f"pytest_meta_dst_{uuid.uuid4().hex[:8]}"
        client.create_folder(src)
        try:
            client.move_resource(src, dst)
            data = client.get_resource(dst).json()
            assert "path" in data, "Поле 'path' отсутствует в метаданных"
            # API возвращает путь в формате disk:/имя_папки
            assert dst in data["path"], (
                f"Поле 'path' должно содержать новый путь '{dst}', "
                f"но содержит: '{data['path']}'"
            )
            assert src not in data["path"], (
                f"Поле 'path' не должно содержать старый путь '{src}'"
            )
        finally:
            client.delete_resource(src, permanently=True)
            client.delete_resource(dst, permanently=True)
