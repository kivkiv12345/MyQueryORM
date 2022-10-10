from typing import Any

if __name__ == '__main__':
    # Gently remind the user to not run enums.py themselves
    raise SystemExit("Hiya (ʘ‿ʘ)╯, it appears you're trying to run init.py instead of app.py. This, sadly, will not work :(")


from .modelfields import StringField
from mysql.connector.cursor import CursorBase
from .orm import DBModel, ModelField, Models, ModelMeta
from itertools import chain


def _isinstanceorsubclass(obj: object | type, _type: type | tuple[type | tuple[Any, ...], ...]):
    return isinstance(obj, _type) or (issubclass(obj, _type) if isinstance(obj, type) else False)


def _get_columns(cursor: CursorBase, db_name: str, table_name: str):
    cursor.execute(f"SHOW COLUMNS FROM {db_name}.{table_name}")
    columndata = *(column for column in cursor),
    # Returns a tuple of the things we need (All metadata for columns, and the primary key column).
    return columndata, next(col[0] for col in columndata if col[3] == 'PRI')


def _add_metadata(model: DBModel, db_name: str):
    # columns, pk_column = _get_columns(cursor, db_name, model.__name__)  # Get the needed column data for the current model.

    # We add Meta to the model after declaration, such that it may refer back to its model.
    # metadata = {
    #     'fields': tuple(ModelField(column) for column in columns),
    #     'fieldnames': tuple(column[0] for column in columns),
    #     'pk_column': pk_column,
    #     'table_name': model.__name__,
    #     'column_data': columns,
    # }

    table_name = model.__name__

    # TODO Kevin: Hardcoded PK field
    model.meta = ModelMeta(table_name + 'ID', table_name, db_name, fields={
        field: value for field, value in (model.__annotations__ | model.__dict__).items() if not field.startswith('__')
    })


def connect_orm(cursor: CursorBase, db_name: str) -> set[DBModel]:
    """
    Connects to the desired database and initialises foreignkey relations between models.

    :param cursor: Cursor to use when querying the database.
    :param db_name: Name of the database to connect to.
    :return: The populated Models set.
    """
    if not cursor or not db_name:
        raise SystemExit("A successful connection to the database must be established before the ORM may be initialized")

    global Models  # Make a reference to the global Models dictionary.

    # cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.execute(f"USE {db_name}")

    for model in Models:
        _add_metadata(model, cursor, db_name)

    # Populate the global _foreignkey_relationships dictionary.
    global _foreignkey_relationships

    # Get all foreignkey relationships in the database.
    cursor.execute(f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE
            REFERENCED_TABLE_SCHEMA = {db_name}
    """)

    for row in cursor:
        if row[0] in _foreignkey_relationships:
            _foreignkey_relationships[row[0]].update({row[1]: (row[3], row[4])})
        else:
            _foreignkey_relationships[row[0]] = {row[1]: (row[3], row[4])}

    return Models


def create_tables(cursor: CursorBase, db_name: str):
    """
    Create tables from models in the database. Constitutes the initial migration.

    :param cursor: Cursor to use when querying the database.
    :param db_name: Name of the database to connect to.
    """

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.execute(f"USE {db_name}")
    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
    table_names = {table_tuple[0] for table_tuple in cursor}

    for model in Models:
        _add_metadata(model, db_name)

    model_names = {model.meta.table_name for model in Models}

    # Sanity check columns on existing tables.
    for table in table_names.intersection(model_names):
        print(f"{db_name}.{table} already exists")

    def _create_typestring(fieldname: str, fieldtype: Any) -> str:
        if _isinstanceorsubclass(fieldtype, StringField):
            return f"{fieldname} varchar({fieldtype.length})"
        elif _isinstanceorsubclass(fieldtype, int):
            return f"{fieldname} int"
        elif _isinstanceorsubclass(fieldtype, DBModel):  # Foreign key
            return f"{fieldtype.meta.pk_column} int"
        else:
            raise TypeError(f"Cannot create column for field of type {fieldtype}")

    def _create_fkstring(fieldtype: DBModel) -> str:
        return f"FOREIGN KEY ({fieldtype.meta.pk_column}) REFERENCES {fieldtype.meta.table_name}({fieldtype.meta.pk_column})"

    # Check for missing tables.
    for model in Models:
        # TODO Kevin: It's possible we try to add Foreign keys before actual tables here, maybe retry until we get things right?
        if model.meta.table_name not in table_names:
            fieldstring = ', '.join(chain(
                # TODO Kevin: Hardcoded stuff here
                (f"{model.meta.pk_column} int NOT NULL",),
                (_create_typestring(fieldname, fieldtype) for fieldname, fieldtype in model.meta.fields.items()),
                (f"PRIMARY KEY ({model.meta.pk_column})",),
                (_create_fkstring(fieldtype) for fieldname, fieldtype in model.meta.fields.items() if _isinstanceorsubclass(fieldtype, DBModel)))
            )

            cursor.execute(f"CREATE TABLE {model.meta.table_name} ({fieldstring});")
