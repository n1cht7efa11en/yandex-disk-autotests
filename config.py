"""
Конфигурация проекта.
Токен читается из переменной окружения YANDEX_TOKEN (файл .env).
"""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL: str = "https://cloud-api.yandex.net/v1/disk"

TOKEN: str = os.getenv("YANDEX_TOKEN", "")

HEADERS: dict = {
    "Authorization": f"OAuth {TOKEN}",
    "Accept": "application/json",
}
