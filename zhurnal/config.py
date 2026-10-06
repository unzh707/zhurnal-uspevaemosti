import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Базовая конфигурация приложения."""

    # Секретный ключ нужен Flask для подписи сессий и cookie.
    # В реальном проекте его следует брать из переменной окружения.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Строка подключения к базе данных SQLite.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "zhurnal.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Сколько дней помнить пользователя, если он отметил "Запомнить меня".
    REMEMBER_COOKIE_DURATION_DAYS = 14
