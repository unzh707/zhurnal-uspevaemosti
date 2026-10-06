import os
from datetime import timedelta

from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app(config_class: type = Config) -> Flask:
    """Фабрика приложения: создаёт и настраивает экземпляр Flask."""

    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(
        days=app.config.get("REMEMBER_COOKIE_DURATION_DAYS", 14)
    )

    # Убеждаемся, что папка instance/ (там лежит sqlite-файл) существует.
    instance_path = os.path.join(app.root_path, "..", "instance")
    os.makedirs(instance_path, exist_ok=True)

    # --- инициализация расширений --------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # --- security-заголовки (частично закрывают требования по XSS) ------
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    # --- регистрация Blueprint'ов ---------------------------------------
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # --- обработчики ошибок ----------------------------------------------
    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template
        return render_template("errors/404.html"), 404

    # --- создание таблиц при первом запуске -------------------------------
    with app.app_context():
        db.create_all()

    return app
