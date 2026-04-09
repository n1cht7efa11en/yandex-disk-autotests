import requests

from config import BASE_URL


class TestUnauthorized:

    def test_get_disk_info_without_token_returns_401(self) -> None:
        response = requests.get(BASE_URL)
        assert response.status_code == 401, (
            f"Запрос без токена должен возвращать 401, получен {response.status_code}"
        )

    def test_get_disk_info_with_invalid_token_returns_401(self) -> None:
        headers = {"Authorization": "OAuth invalid_token_xyz_12345"}
        response = requests.get(BASE_URL, headers=headers)
        assert response.status_code == 401

    def test_get_resource_without_token_returns_401(self) -> None:
        resp = requests.get(f"{BASE_URL}/resources", params={"path": "/"})
        assert resp.status_code == 401

    def test_create_folder_without_token_returns_401(self) -> None:
        response = requests.put(
            f"{BASE_URL}/resources", params={"path": "unauthorized_test_folder"}
        )
        assert response.status_code == 401

    def test_delete_without_token_returns_401(self) -> None:
        response = requests.delete(
            f"{BASE_URL}/resources", params={"path": "some_path"}
        )
        assert response.status_code == 401

    def test_error_response_contains_description(self) -> None:
        """401 должен возвращать тело с описанием ошибки."""
        data = requests.get(BASE_URL).json()
        assert "description" in data or "message" in data
