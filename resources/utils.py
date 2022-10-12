from mysql.connector import MySQLConnection
from mysql.connector.cursor import CursorBase


class _SingletonMeta(type):
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instance[cls]


class ConnectionSingleton(metaclass=_SingletonMeta):

    connection: MySQLConnection
    cursor: CursorBase
    # commit = True  # Used to allow QuerySet to commit multiple rows

    __slots__ = ['connection', 'cursor']

    def __init__(self, connection: MySQLConnection, cursor: CursorBase) -> None:
        self.connection = connection
        self.cursor = cursor
        super().__init__()
