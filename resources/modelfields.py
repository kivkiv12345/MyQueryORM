from typing import NamedTuple, Any
from resources import orm


class StringField(NamedTuple):
    length: int


class PKField(NamedTuple):
    type: Any


class ForeignkeyField(NamedTuple):
    model: 'orm.DBModel'
    null: bool = None
    on_delete = None
