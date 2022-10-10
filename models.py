""" This is where we define our models for the database. """

from resources.orm import DBModel


class Group(DBModel):
    name: str


class User(DBModel):
    name: str
    age: int
    group: DBModel = Group
