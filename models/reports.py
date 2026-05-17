import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin

from db_session import SqlAlchemyBase


class Report(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'reports'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    reporter_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    entity_type = sqlalchemy.Column(sqlalchemy.String)
    entity_id = sqlalchemy.Column(sqlalchemy.Integer)

    reason = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text)

    status = sqlalchemy.Column(sqlalchemy.String, default='pending')

    reviewed_by = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    reviewed_at = sqlalchemy.Column(sqlalchemy.DateTime)

    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)