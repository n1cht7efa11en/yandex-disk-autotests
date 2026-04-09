# Yandex Disk API — Автотесты

Тестовый проект для автоматизированного тестирования REST API Яндекс.Диска.
Стек: **Python 3 · pytest · requests**

---

## Структура проекта

```
yandex-disk-autotests/
├── config.py              # Конфигурация (базовый URL, заголовки)
├── conftest.py            # Общие фикстуры pytest
├── pytest.ini             # Настройки pytest
├── requirements.txt       # Зависимости
├── .env.example           # Шаблон файла с токеном
├── utils/
│   └── disk_client.py     # Обёртка над requests для Яндекс.Диска API
└── tests/
    ├── test_auth.py       # Проверка авторизации: 401 без токена / с неверным токеном
    ├── test_get.py        # GET-методы: инфо о диске, метаданные, список файлов
    ├── test_put.py        # PUT-методы: создание папки, загрузка файла, конфликты
    ├── test_post.py       # POST-методы: копирование, перемещение, конфликты
    ├── test_delete.py     # DELETE-методы: удаление ресурсов
    ├── test_trash.py      # Корзина: мягкое удаление, восстановление, очистка
    └── test_advanced.py   # Расширенные: целостность данных, async, граничные значения
```

---

## Получение OAuth-токена

> Токен нужен для доступа к API. Используйте **тестовое приложение Яндекса** — не свой личный аккаунт.

### Способ 1 — через Полигон (быстро, для тестирования)

1. Откройте [Полигон Яндекс.Диска](https://yandex.ru/dev/disk/poligon/).
2. Войдите в тестовый Яндекс-аккаунт (создайте отдельный, если нужно).
3. Нажмите **«Получить OAuth-токен»** — токен появится в правом верхнем углу.
4. Скопируйте токен.

### Способ 2 — через OAuth-приложение (рекомендуется для CI)

1. Зайдите на [oauth.yandex.ru](https://oauth.yandex.ru/) и создайте новое приложение.
2. В разделе **«Права»** выберите:
   - `cloud_api:disk.read`
   - `cloud_api:disk.write`
   - `cloud_api:disk.app_folder`
3. В поле **«Redirect URI»** укажите `https://oauth.yandex.ru/verification_code`.
4. Сохраните приложение и скопируйте **Client ID**.
5. Откройте в браузере:
   ```
   https://oauth.yandex.ru/authorize?response_type=token&client_id=<YOUR_CLIENT_ID>
   ```
6. Разрешите доступ — токен появится в адресной строке после `access_token=`.

---

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/<your-username>/yandex-disk-autotests.git
cd yandex-disk-autotests
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Добавить токен

```bash
cp .env.example .env
```

Откройте `.env` и вставьте ваш токен:

```
YANDEX_TOKEN=ваш_токен_здесь
```

### 5. Запустить тесты

```bash
# Все тесты
pytest

# Конкретный файл
pytest tests/test_get.py

# Конкретный класс или метод
pytest tests/test_put.py::TestCreateFolder::test_create_folder_returns_201

# С HTML-отчётом
pytest --html=reports/report.html --self-contained-html
```

---

## Покрываемые методы API

| HTTP-метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/v1/disk` | Информация о диске |
| `GET` | `/v1/disk/resources` | Метаданные файла/папки |
| `GET` | `/v1/disk/resources/files` | Плоский список файлов |
| `GET` | `/v1/disk/resources/upload` | Получить URL для загрузки |
| `GET` | `/v1/disk/trash/resources` | Содержимое корзины |
| `GET` | `/v1/disk/operations` | Статус асинхронной операции |
| `PUT` | `/v1/disk/resources` | Создать папку |
| `PUT` | `<upload_url>` | Загрузить файл |
| `PUT` | `/v1/disk/trash/resources/restore` | Восстановить из корзины |
| `POST` | `/v1/disk/resources/copy` | Скопировать ресурс |
| `POST` | `/v1/disk/resources/move` | Переместить / переименовать |
| `DELETE` | `/v1/disk/resources` | Удалить ресурс (навсегда или в корзину) |
| `DELETE` | `/v1/disk/trash/resources` | Очистить корзину / удалить из корзины |

---

## Примечания

- Тесты используют изолированные временные папки с префиксом `pytest_autotests_` — они создаются и удаляются автоматически.
- Файл `.env` добавлен в `.gitignore` и **никогда не попадёт в репозиторий**.
- Документация API: https://yandex.ru/dev/disk/api/concepts/about-docpage/
