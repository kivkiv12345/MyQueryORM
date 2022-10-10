from typing import NamedTuple, Any
from resources.orm import DBModel


class StringField(NamedTuple):
    length: int


class PKField(NamedTuple):
    type: Any


class ForeignkeyField(NamedTuple):
    model: DBModel
    null: bool = None
    on_delete = None
