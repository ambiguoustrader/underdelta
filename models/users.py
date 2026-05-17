import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    password_hash = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    rating = sqlalchemy.Column(sqlalchemy.Integer, default=1000)
    level = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    xp = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    is_admin = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    banned_by = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    banned_at = sqlalchemy.Column(sqlalchemy.DateTime)
    ban_reason = sqlalchemy.Column(sqlalchemy.String)

    solved_count = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    correct_count = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    wins = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    losses = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    subject_stats = sqlalchemy.Column(sqlalchemy.Text, default='{}')

    last_login = sqlalchemy.Column(sqlalchemy.DateTime)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    avatar_url = sqlalchemy.Column(sqlalchemy.String, default='/static/images/standart.png')
    bio = sqlalchemy.Column(sqlalchemy.String)
    favorite_character = sqlalchemy.Column(sqlalchemy.String)

    total_playtime = sqlalchemy.Column(sqlalchemy.Float, default=0.0)
    streak_days = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    last_active_date = sqlalchemy.Column(sqlalchemy.DateTime)

    sessions = orm.relationship("Session", back_populates="user", cascade="all, delete")
    tasks = orm.relationship("Task", back_populates="creator")