"""
Расширенные тесты API Яндекс.Диска.

Покрывают нетривиальные сценарии, которые выходят за рамки базовой проверки
статус-кодов:

  1. TestDataIntegrity     — целостность данных: MD5 загруженного = MD5 скачанного
  2. TestAsyncOperations   — отслеживание асинхронных операций через /operations
  3. TestDiskSpaceTracking — изменение used_space после загрузки файла
  4. TestBoundaryValues    — граничные значения: длина имени, кириллица, спецсимволы
  5. TestParametrized      — параметризованные тесты для разных типов файлов
"""
import hashlib
import time
import uuid

import pytest

from utils.disk_client import DiskApiClient


# ─────────────────────────────────────────────────────────────────────────────
# 1. Целостность данных
# ─────────────────────────────────────────────────────────────────────────────

class TestDataIntegrity:
    """
    Проверяет, что файл после загрузки на Диск и последующего скачивания
    не изменился — MD5-хеш оригинала совпадает с хешем скачанного файла.
    """

    def test_uploaded_file_content_matches_original(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        original_data = b"Hello, Yandex Disk! Data integrity check."
        original_md5 = hashlib.md5(original_data).hexdigest()

        file_path = f"{test_folder}/integrity_check.txt"
        upload_resp = client.upload_file(file_path, original_data, overwrite=True)
        assert upload_resp.status_code == 201, (
            f"Загрузка не удалась: {upload_resp.status_code}"
        )

        download_resp = client.download_file(file_path)
        assert download_resp.status_code == 200, (
            f"Скачивание не удалось: {download_resp.status_code}"
        )

        downloaded_md5 = hashlib.md5(download_resp.content).hexdigest()
        assert original_md5 == downloaded_md5, (
            f"MD5 не совпадает: оригинал={original_md5}, скачанный={downloaded_md5}"
        )

    def test_binary_file_integrity(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        """Целостность бинарных данных (не только текст)."""
        binary_data = bytes(range(256)) * 10  # 2560 байт со всеми возможными байтами
        original_md5 = hashlib.md5(binary_data).hexdigest()

        file_path = f"{test_folder}/binary_integrity.bin"
        client.upload_file(file_path, binary_data, overwrite=True)

        downloaded = client.download_file(file_path)
        assert hashlib.md5(downloaded.content).hexdigest() == original_md5

    def test_empty_file_integrity(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        """Пустой файл (0 байт) должен загружаться и скачиваться без ошибок."""
        file_path = f"{test_folder}/empty_file.txt"
        upload_resp = client.upload_file(file_path, b"", overwrite=True)
        assert upload_resp.status_code == 201

        download_resp = client.download_file(file_path)
        assert download_resp.status_code == 200
        assert download_resp.content == b""


# ─────────────────────────────────────────────────────────────────────────────
# 2. Отслеживание асинхронных операций
# ─────────────────────────────────────────────────────────────────────────────

class TestAsyncOperations:
    """
    Когда API возвращает 202 Accepted, он отдаёт ссылку на /operations?id=...
    Тесты проверяют, что операция доходит до статуса 'success'.
    """

    def _wait_for_operation(
        self, client: DiskApiClient, operation_id: str,
        timeout: int = 10, interval: float = 0.5
    ) -> str:
        """Polling операции до получения конечного статуса или timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = client.get_operation_status(operation_id)
            if resp.status_code == 404:
                # Операция завершилась раньше, чем мы успели её запросить
                return "success"
            assert resp.status_code == 200, (
                f"Ошибка при запросе статуса операции: {resp.status_code}"
            )
            status = resp.json().get("status")
            if status in ("success", "failed"):
                return status
            time.sleep(interval)
        return "timeout"

    def test_delete_nonempty_folder_async_completes(
        self, client: DiskApiClient, test_file: str, test_folder: str
    ) -> None:
        """
        Удаление непустой папки возвращает 202 + operation_id.
        Операция должна завершиться статусом 'success'.
        """
        response = client.delete_resource(test_folder, permanently=True)

        if response.status_code == 204:
            pytest.skip("Папка удалилась синхронно (204), async-тест не применим")

        assert response.status_code == 202, (
            f"Ожидался 202, получен {response.status_code}"
        )

        operation_url = response.json().get("href", "")
        assert operation_url, "Ответ 202 должен содержать href на операцию"

        # Извлекаем id из URL вида .../operations?id=<id>
        operation_id = operation_url.split("id=")[-1]
        final_status = self._wait_for_operation(client, operation_id)

        assert final_status == "success", (
            f"Операция завершилась со статусом '{final_status}', ожидался 'success'"
        )

    def test_copy_nonempty_folder_async_completes(
        self, client: DiskApiClient, test_file: str, test_folder: str
    ) -> None:
        """
        Копирование непустой папки возвращает 202.
        Проверяем, что операция завершается успехом.
        """
        copy_path = f"{test_folder}_async_copy"
        try:
            response = client.copy_resource(test_folder, copy_path)

            if response.status_code == 201:
                pytest.skip("Копирование завершилось синхронно (201)")

            assert response.status_code == 202
            operation_id = response.json()["href"].split("id=")[-1]
            final_status = self._wait_for_operation(client, operation_id)
            assert final_status == "success"
        finally:
            client.delete_resource(copy_path, permanently=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Отслеживание используемого места
# ─────────────────────────────────────────────────────────────────────────────

class TestDiskSpaceTracking:
    """
    Проверяет, что used_space на диске корректно увеличивается
    после загрузки файла.
    """

    def test_used_space_increases_after_upload(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        used_before = client.get_disk_info().json()["used_space"]

        file_content = b"x" * 512_000  # 500 КБ — достаточно чтобы used_space обновился
        file_path = f"{test_folder}/space_check.txt"
        upload_resp = client.upload_file(file_path, file_content, overwrite=True)
        assert upload_resp.status_code == 201

        used_after = client.get_disk_info().json()["used_space"]
        assert used_after > used_before, (
            f"used_space не увеличился: было {used_before}, стало {used_after}"
        )

    def test_used_space_decreases_after_delete(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        file_content = b"y" * 2048
        file_path = f"{test_folder}/space_delete_check.txt"
        client.upload_file(file_path, file_content, overwrite=True)

        used_after_upload = client.get_disk_info().json()["used_space"]
        client.delete_resource(file_path, permanently=True)

        used_after_delete = client.get_disk_info().json()["used_space"]
        assert used_after_delete < used_after_upload, (
            "used_space должен уменьшиться после безвозвратного удаления файла"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Граничные значения
# ─────────────────────────────────────────────────────────────────────────────

class TestBoundaryValues:
    """
    Проверяет поведение API на граничных значениях, задокументированных
    в официальной документации: длина пути, кириллица, спецсимволы.
    """

    def test_max_length_folder_name(self, client: DiskApiClient) -> None:
        """Максимальная длина имени папки по документации — 255 символов."""
        max_name = "a" * 255
        try:
            response = client.create_folder(max_name)
            assert response.status_code == 201, (
                f"Папка с именем 255 символов должна создаваться: {response.text}"
            )
        finally:
            client.delete_resource(max_name, permanently=True)

    def test_exceeding_max_length_folder_name(self, client: DiskApiClient) -> None:
        """Имя папки длиннее 255 символов должно вернуть ошибку."""
        too_long_name = "a" * 256
        response = client.create_folder(too_long_name)
        assert response.status_code in (400, 404, 422), (
            f"Имя > 255 символов должно возвращать ошибку, получен {response.status_code}"
        )

    def test_cyrillic_folder_name(self, client: DiskApiClient) -> None:
        """Кириллические имена папок должны поддерживаться."""
        name = f"Тестовая_папка_{uuid.uuid4().hex[:4]}"
        try:
            response = client.create_folder(name)
            assert response.status_code == 201, (
                f"Кириллическое имя папки должно работать: {response.text}"
            )
            # Проверяем, что папка реально доступна по кириллическому пути
            get_resp = client.get_resource(name)
            assert get_resp.status_code == 200
            assert get_resp.json()["name"] == name
        finally:
            client.delete_resource(name, permanently=True)

    def test_cyrillic_file_name(
        self, client: DiskApiClient, test_folder: str
    ) -> None:
        """Кириллические имена файлов должны поддерживаться."""
        file_path = f"{test_folder}/файл_с_данными.txt"
        upload_resp = client.upload_file(file_path, "Привет, мир!".encode("utf-8"))
        assert upload_resp.status_code == 201

        get_resp = client.get_resource(file_path)
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "файл_с_данными.txt"

    def test_nested_folder_path(self, client: DiskApiClient) -> None:
        """Создание папки по вложенному пути — должна вернуть 409,
        если родительский каталог не существует."""
        path = f"nonexistent_parent_{uuid.uuid4().hex[:6]}/child_folder"
        response = client.create_folder(path)
        assert response.status_code in (404, 409), (
            f"Вложенный путь без родителя должен возвращать ошибку, "
            f"получен {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Параметризованные тесты
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("filename,content,description", [
    ("text_file.txt",   b"Plain text content",                    "текстовый файл"),
    ("empty_file.txt",  b"",                                      "пустой файл (0 байт)"),
    ("json_file.json",  b'{"key": "value", "number": 42}',       "JSON-файл"),
    ("binary_file.bin", bytes(range(256)),                        "бинарный файл"),
    ("large_file.txt",  b"A" * 100_000,                          "файл 100 КБ"),
], ids=["текстовый файл", "пустой файл", "JSON-файл", "бинарный файл", "файл 100 КБ"])
class TestParametrized:
    """
    Параметризованные тесты загрузки и скачивания файлов разных типов.
    Каждый сценарий проверяет полный цикл: загрузка → метаданные → скачивание.
    """

    def test_upload_various_file_types(
        self,
        client: DiskApiClient,
        test_folder: str,
        filename: str,
        content: bytes,
        description: str,
    ) -> None:
        file_path = f"{test_folder}/{filename}"
        response = client.upload_file(file_path, content, overwrite=True)
        assert response.status_code == 201, (
            f"[{description}] Загрузка не удалась: {response.status_code}"
        )

    def test_uploaded_file_metadata(
        self,
        client: DiskApiClient,
        test_folder: str,
        filename: str,
        content: bytes,
        description: str,
    ) -> None:
        file_path = f"{test_folder}/{filename}"
        client.upload_file(file_path, content, overwrite=True)

        meta = client.get_resource(file_path).json()
        assert meta["name"] == filename, (
            f"[{description}] Имя файла в метаданных не совпадает"
        )
        assert meta["type"] == "file", (
            f"[{description}] Тип ресурса должен быть 'file'"
        )
        assert meta["size"] == len(content), (
            f"[{description}] Размер файла {meta['size']} != {len(content)}"
        )

    def test_download_matches_upload(
        self,
        client: DiskApiClient,
        test_folder: str,
        filename: str,
        content: bytes,
        description: str,
    ) -> None:
        file_path = f"{test_folder}/{filename}"
        client.upload_file(file_path, content, overwrite=True)

        downloaded = client.download_file(file_path)
        assert downloaded.status_code == 200
        assert downloaded.content == content, (
            f"[{description}] Содержимое после скачивания не совпадает с оригиналом"
        )
