"""
Единые экземпляры расширений Flask.

Вынесены в отдельный модуль, чтобы их можно было импортировать
и в models.py, и в фабрике приложения (app/__init__.py) без
циклических импортов.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
# Если анонимный пользователь пытается открыть страницу с @login_required,
# его перенаправит на эту view-функцию.
login_manager.login_view = "auth.login"
login_manager.login_message = "Пожалуйста, войдите в систему, чтобы получить доступ к этой странице."
login_manager.login_message_category = "warning"
