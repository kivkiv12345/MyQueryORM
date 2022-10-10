""" This is where we define our models for the database. """

from resources.orm import DBModel
from resources.modelfields import StringField


class NotSQLGroup(DBModel):
    name: str = StringField(64)


class User(DBModel):
    name: str = StringField(64)
    age: int
    group: DBModel = NotSQLGroup
