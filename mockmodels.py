from resources import DBModel
from resources.modelfields import StringField


class NotSQLGroup(DBModel):
    name: str = StringField(64)


class User(DBModel):
    name: str = StringField(64)
    group: DBModel = NotSQLGroup
