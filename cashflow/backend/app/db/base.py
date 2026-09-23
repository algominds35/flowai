from sqlalchemy.orm import DeclarativeBase
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


class Base(DeclarativeBase):
    pass


# Import all models so Alembic can detect them
from app.models import *  # noqa: F401, E402
