import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

class Task(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    subject = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    difficulty = sqlalchemy.Column(sqlalchemy.String)
    topic = sqlalchemy.Column(sqlalchemy.String)

    question = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    options = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    answer = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    hint = sqlalchemy.Column(sqlalchemy.String, default='')

    created_by = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    creator = orm.relationship("User", back_populates="tasks")