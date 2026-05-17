import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin

from db_session import SqlAlchemyBase


class IcebergFact(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'iceberg_facts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    content = sqlalchemy.Column(sqlalchemy.Text, nullable=False)

    level = sqlalchemy.Column(sqlalchemy.Integer)
    position_x = sqlalchemy.Column(sqlalchemy.Integer)
    position_y = sqlalchemy.Column(sqlalchemy.Integer)

    image_url = sqlalchemy.Column(sqlalchemy.String)
    is_visible = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    views_count = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)