import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class QuizAttempt(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'quiz_attempts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    task_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("tasks.id"))

    user_answer = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    is_correct = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
    time_spent = sqlalchemy.Column(sqlalchemy.Float)

    attempted_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)