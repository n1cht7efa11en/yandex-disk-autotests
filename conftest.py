"""
Общие фикстуры pytest для тестов Яндекс.Диска.
"""
import uuid

import pytest

from config import TOKEN
from utils.disk_client import DiskApiClient

_TEST_PREFIX = "pytest_autotests_"


@pytest.fixture(scope="session")
def client() -> DiskApiClient:
    """
    Сессионный экземпляр API-клиента.
    Пропускает все тесты, если токен не задан.
    """
    if not TOKEN:
        pytest.skip(
            "YANDEX_TOKEN не задан. "
            "Добавьте токен в файл .env (см. .env.example и README.md)."
        )
    return DiskApiClient()


@pytest.fixture
def test_folder(client: DiskApiClient) -> str:
    """
    Создаёт уникальную временную папку перед тестом
    и удаляет её (вместе с содержимым) после.
    """
    folder_name = f"{_TEST_PREFIX}{uuid.uuid4().hex[:10]}"
    response = client.create_folder(folder_name)
    assert response.status_code == 201, (
        f"Не удалось создать тестовую папку '{folder_name}': {response.text}"
    )
    yield folder_name
    client.delete_resource(folder_name, permanently=True)


@pytest.fixture
def test_file(client: DiskApiClient, test_folder: str) -> str:
    """
    Загружает тестовый файл внутри test_folder.
    Файл удаляется вместе с папкой по завершении test_folder-фикстуры.
    """
    file_path = f"{test_folder}/test_file.txt"
    response = client.upload_file(file_path, b"Hello, Yandex Disk!")
    assert response.status_code == 201, (
        f"Не удалось загрузить тестовый файл '{file_path}': {response.text}"
    )
    yield file_path
