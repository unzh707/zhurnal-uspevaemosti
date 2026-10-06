from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, login_manager
from app.models import Teacher, TeacherProfile

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login использует эту функцию, чтобы восстановить пользователя из сессии."""
    return Teacher.query.get(int(user_id))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # --- получаем данные формы регистрации (POST, request.form) -----
        username = request.form.get("username", "").strip()
        last_name = request.form.get("last_name", "").strip()
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        errors = []
        if len(username) < 3:
            errors.append("Логин должен содержать не менее 3 символов.")
        if not last_name:
            errors.append("Укажите фамилию преподавателя.")
        if not first_name:
            errors.append("Укажите имя преподавателя.")
        if len(password) < 6:
            errors.append("Пароль должен содержать не менее 6 символов.")
        if password != password2:
            errors.append("Пароли не совпадают.")
        if Teacher.query.filter_by(username=username).first() is not None:
            errors.append("Такой логин уже занят, выберите другой.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "auth/register.html",
                username=username,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
            )

        # --- создаём преподавателя и его профиль (one-to-one) -----------
        teacher = Teacher(username=username)
        teacher.set_password(password)
        teacher.profile = TeacherProfile(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name or None,
            email=email,
        )

        db.session.add(teacher)
        db.session.commit()

        flash("Регистрация прошла успешно. Теперь вы можете войти.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        teacher = Teacher.query.filter_by(username=username).first()

        if teacher is None or not teacher.check_password(password):
            flash("Неверный логин или пароль.", "danger")
            return render_template("auth/login.html", username=username)

        login_user(teacher, remember=remember)
        flash(f"Добро пожаловать, {teacher.profile.full_name if teacher.profile else teacher.username}!", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("auth.login"))
