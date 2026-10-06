"""
Модели ORM для проекта «Учёт успеваемости (Журнал)».

Реализованные связи (согласно техническому заданию):
    * one-to-one   — Teacher  <-> TeacherProfile
    * one-to-many  — Teacher  ->  Group
    * one-to-many  — Group    ->  Student
    * one-to-many  — Student  ->  Grade
    * one-to-many  — Subject  ->  Grade
    * many-to-many — Group    <-> Subject   (через таблицу group_subjects)
"""
from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


# ---------------------------------------------------------------------------
# Вспомогательная таблица для связи many-to-many между Group и Subject.
# У неё нет собственной модели — только внешние ключи, как принято для
# "чистых" связующих таблиц в SQLAlchemy.
# ---------------------------------------------------------------------------
group_subjects = db.Table(
    "group_subjects",
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subjects.id"), primary_key=True),
)


class Teacher(UserMixin, db.Model):
    """Преподаватель — единственная роль пользователя, которая логинится в систему."""

    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # one-to-one: у каждого преподавателя может быть ровно один профиль
    profile = db.relationship(
        "TeacherProfile",
        backref="teacher",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # one-to-many: у преподавателя может быть много групп
    groups = db.relationship(
        "Group",
        backref="teacher",
        cascade="all, delete-orphan",
        order_by="Group.name",
    )

    def set_password(self, raw_password: str) -> None:
        """Хеширует пароль с солью (PBKDF2-SHA256) перед сохранением."""
        self.password_hash = generate_password_hash(raw_password, method="pbkdf2:sha256")

    def check_password(self, raw_password: str) -> bool:
        """Сверяет введённый пароль с хешем в базе данных."""
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<Teacher {self.username}>"


class TeacherProfile(db.Model):
    """Дополнительные сведения о преподавателе (one-to-one к Teacher)."""

    __tablename__ = "teacher_profiles"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), unique=True, nullable=False
    )
    last_name = db.Column(db.String(60), nullable=False)
    first_name = db.Column(db.String(60), nullable=False)
    middle_name = db.Column(db.String(60))  # отчество — необязательное поле
    email = db.Column(db.String(150))
    phone = db.Column(db.String(30))

    @property
    def full_name(self):
        """Фамилия Имя Отчество одной строкой (для заголовков, приветствий и т.п.)."""
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    def __repr__(self):
        return f"<TeacherProfile {self.full_name}>"


class Group(db.Model):
    """Учебная группа, которую ведёт преподаватель."""

    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # one-to-many: в группе много студентов
    students = db.relationship(
        "Student",
        backref="group",
        cascade="all, delete-orphan",
        order_by="Student.last_name, Student.first_name",
    )

    # many-to-many: в группе изучается несколько предметов,
    # и один предмет может изучаться в нескольких группах
    subjects = db.relationship(
        "Subject",
        secondary=group_subjects,
        backref=db.backref("groups", lazy="dynamic"),
    )

    def __repr__(self):
        return f"<Group {self.name}>"


class Student(db.Model):
    """Студент внутри группы."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(60), nullable=False)
    first_name = db.Column(db.String(60), nullable=False)
    middle_name = db.Column(db.String(60))  # отчество — необязательное поле
    birth_date = db.Column(db.Date, nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # one-to-many: у студента много оценок
    grades = db.relationship(
        "Grade",
        backref="student",
        cascade="all, delete-orphan",
        order_by="Grade.date_given.desc()",
    )

    @property
    def full_name(self):
        """Фамилия Имя Отчество одной строкой — для таблиц, заголовков, поиска."""
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    @property
    def average_grade(self):
        """Средний балл студента по всем предметам (или None, если оценок нет)."""
        if not self.grades:
            return None
        return round(sum(g.value for g in self.grades) / len(self.grades), 2)

    def average_for_subject(self, subject_id):
        """Средний балл студента по конкретному предмету."""
        subject_grades = [g.value for g in self.grades if g.subject_id == subject_id]
        if not subject_grades:
            return None
        return round(sum(subject_grades) / len(subject_grades), 2)

    def __repr__(self):
        return f"<Student {self.full_name}>"


class Subject(db.Model):
    """Учебная дисциплина."""

    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    # one-to-many: по предмету много оценок
    grades = db.relationship("Grade", backref="subject")

    def __repr__(self):
        return f"<Subject {self.name}>"


class Grade(db.Model):
    """Оценка студента по предмету."""

    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)  # 2..5 по российской шкале
    date_given = db.Column(db.Date, default=date.today, nullable=False)
    comment = db.Column(db.String(255))

    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)

    def __repr__(self):
        return f"<Grade {self.value} student={self.student_id} subject={self.subject_id}>"
