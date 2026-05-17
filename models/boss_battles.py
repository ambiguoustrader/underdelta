import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin


class BossBattle(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'boss_battles'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    boss_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    boss_description = sqlalchemy.Column(sqlalchemy.Text)

    boss_hp = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    boss_image = sqlalchemy.Column(sqlalchemy.String)

    difficulty_level = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    reward_xp = sqlalchemy.Column(sqlalchemy.Integer, default=100)
    unlock_level = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)