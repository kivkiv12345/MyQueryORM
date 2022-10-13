""" This is where we define our models for the database. """

from resources.orm import DBModel
from resources.modelfields import StringField


class NotSQLGroup(DBModel):
    name: str = StringField(64)


class User(DBModel):
    name: str = StringField(64)
    age: int = 0  # TODO Kevin: Should it be possible to create fields from annotations alone?
    group: DBModel = NotSQLGroup
