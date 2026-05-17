import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class Session(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'sessions'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    token = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)

    ip_address = sqlalchemy.Column(sqlalchemy.String)
    user_agent = sqlalchemy.Column(sqlalchemy.String)

    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    user = orm.relationship("User", back_populates="sessions")