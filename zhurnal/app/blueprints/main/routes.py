from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Group, Student, Subject, Grade, TeacherProfile

main_bp = Blueprint("main", __name__)


def _get_own_group_or_404(group_id):
    """Возвращает группу текущего преподавателя или 404, если это не его группа.

    Это и есть та самая "изоляция данных": преподаватель не может ни увидеть,
    ни отредактировать чужую группу, даже подобрав её id вручную в адресной строке.
    """
    group = Group.query.filter_by(id=group_id, teacher_id=current_user.id).first()
    if group is None:
        abort(404)
    return group


# ---------------------------------------------------------------------------
# Главная страница: список групп преподавателя + поиск/фильтрация (GET)
# ---------------------------------------------------------------------------
@main_bp.route("/")
@login_required
def dashboard():
    # Поиск по названию группы через query-параметр (?q=...)
    query = request.args.get("q", "").strip()

    groups_query = Group.query.filter_by(teacher_id=current_user.id)
    if query:
        groups_query = groups_query.filter(Group.name.ilike(f"%{query}%"))

    groups = groups_query.order_by(Group.name).all()

    return render_template("main/dashboard.html", groups=groups, query=query)


@main_bp.route("/groups/new", methods=["POST"])
@login_required
def create_group():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Введите название группы.", "danger")
        return redirect(url_for("main.dashboard"))

    group = Group(name=name, teacher_id=current_user.id)
    db.session.add(group)
    db.session.commit()
    flash(f"Группа «{name}» создана.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    group = _get_own_group_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    flash("Группа удалена вместе со всеми студентами.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# Страница группы: студенты, предметы, поиск студентов внутри группы (GET)
# ---------------------------------------------------------------------------
@main_bp.route("/groups/<int:group_id>")
@login_required
def group_detail(group_id):
    group = _get_own_group_or_404(group_id)

    # Фильтрация студентов по имени через query-параметр (?search=...)
    search = request.args.get("search", "").strip()

    students = group.students
    if search:
        students = [s for s in students if search.lower() in s.full_name.lower()]

    all_subjects = Subject.query.order_by(Subject.name).all()

    return render_template(
        "main/group.html",
        group=group,
        students=students,
        search=search,
        all_subjects=all_subjects,
    )


@main_bp.route("/groups/<int:group_id>/students/new", methods=["POST"])
@login_required
def add_student(group_id):
    group = _get_own_group_or_404(group_id)

    last_name = request.form.get("last_name", "").strip()
    first_name = request.form.get("first_name", "").strip()
    middle_name = request.form.get("middle_name", "").strip()
    birth_date_raw = request.form.get("birth_date", "").strip()

    if not last_name or not first_name:
        flash("Укажите фамилию и имя студента.", "danger")
        return redirect(url_for("main.group_detail", group_id=group.id))

    birth_date = None
    if birth_date_raw:
        try:
            birth_date = datetime.strptime(birth_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Дата рождения указана в неверном формате.", "danger")
            return redirect(url_for("main.group_detail", group_id=group.id))

    student = Student(
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name or None,
        birth_date=birth_date,
        group_id=group.id,
    )
    db.session.add(student)
    db.session.commit()
    flash(f"Студент «{student.full_name}» добавлен в группу.", "success")
    return redirect(url_for("main.group_detail", group_id=group.id))


@main_bp.route("/groups/<int:group_id>/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(group_id, student_id):
    group = _get_own_group_or_404(group_id)
    student = Student.query.filter_by(id=student_id, group_id=group.id).first_or_404()
    db.session.delete(student)
    db.session.commit()
    flash("Студент удалён из группы.", "info")
    return redirect(url_for("main.group_detail", group_id=group.id))


@main_bp.route("/groups/<int:group_id>/subjects", methods=["POST"])
@login_required
def link_subject(group_id):
    """Привязывает предмет к группе (демонстрация связи many-to-many)."""
    group = _get_own_group_or_404(group_id)

    subject_name = request.form.get("subject_name", "").strip()
    if not subject_name:
        flash("Укажите название предмета.", "danger")
        return redirect(url_for("main.group_detail", group_id=group.id))

    subject = Subject.query.filter_by(name=subject_name).first()
    if subject is None:
        subject = Subject(name=subject_name)
        db.session.add(subject)

    if subject not in group.subjects:
        group.subjects.append(subject)
        db.session.commit()
        flash(f"Предмет «{subject_name}» добавлен в группу.", "success")
    else:
        flash("Этот предмет уже привязан к группе.", "warning")

    return redirect(url_for("main.group_detail", group_id=group.id))


# ---------------------------------------------------------------------------
# Страница студента: оценки и средний балл
# ---------------------------------------------------------------------------
@main_bp.route("/students/<int:student_id>")
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    group = _get_own_group_or_404(student.group_id)  # проверка прав доступа

    all_subjects = Subject.query.order_by(Subject.name).all()

    return render_template(
        "main/student.html",
        student=student,
        group=group,
        all_subjects=all_subjects,
    )


@main_bp.route("/students/<int:student_id>/grades/new", methods=["POST"])
@login_required
def add_grade(student_id):
    student = Student.query.get_or_404(student_id)
    _get_own_group_or_404(student.group_id)  # проверка прав доступа

    subject_id = request.form.get("subject_id", type=int)
    value = request.form.get("value", type=int)
    comment = request.form.get("comment", "").strip()

    if subject_id is None or value is None:
        flash("Заполните предмет и оценку.", "danger")
        return redirect(url_for("main.student_detail", student_id=student.id))

    if value < 2 or value > 5:
        flash("Оценка должна быть в диапазоне от 2 до 5.", "danger")
        return redirect(url_for("main.student_detail", student_id=student.id))

    grade = Grade(
        student_id=student.id,
        subject_id=subject_id,
        value=value,
        comment=comment or None,
    )
    db.session.add(grade)
    db.session.commit()
    flash("Оценка выставлена.", "success")
    return redirect(url_for("main.student_detail", student_id=student.id))


@main_bp.route("/grades/<int:grade_id>/delete", methods=["POST"])
@login_required
def delete_grade(grade_id):
    grade = Grade.query.get_or_404(grade_id)
    student = Student.query.get_or_404(grade.student_id)
    _get_own_group_or_404(student.group_id)  # проверка прав доступа

    db.session.delete(grade)
    db.session.commit()
    flash("Оценка удалена.", "info")
    return redirect(url_for("main.student_detail", student_id=student.id))


# ---------------------------------------------------------------------------
# Профиль преподавателя (one-to-one Teacher <-> TeacherProfile)
# ---------------------------------------------------------------------------
@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.profile is None:
        # Подстраховка на случай старого аккаунта без профиля.
        current_user.profile = TeacherProfile(
            last_name=current_user.username, first_name=""
        )
        db.session.commit()

    if request.method == "POST":
        last_name = request.form.get("last_name", "").strip()
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()

        if not last_name or not first_name:
            flash("Укажите фамилию и имя.", "danger")
            return render_template("main/profile.html")

        current_user.profile.last_name = last_name
        current_user.profile.first_name = first_name
        current_user.profile.middle_name = middle_name or None
        current_user.profile.email = request.form.get("email", "").strip()
        current_user.profile.phone = request.form.get("phone", "").strip()
        db.session.commit()
        flash("Профиль обновлён.", "success")
        return redirect(url_for("main.profile"))

    return render_template("main/profile.html")
