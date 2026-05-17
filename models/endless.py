import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin

from db_session import SqlAlchemyBase


class EndlessModeRecord(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'endless_mode_records'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))

    time_survived = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    enemies_defeated = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    waves_completed = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    score = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    achieved_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)