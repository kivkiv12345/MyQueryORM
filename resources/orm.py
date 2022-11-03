"""
Stores database data and queryset models.
"""
from types import NoneType

from resources.modelfields import StringField

if __name__ == '__main__':
    # Gently remind the user to not run program.py themselves
    raise SystemExit("(⊙＿⊙') Wha!?... Are you trying to run orm.py?\n"
                     " You know this is a bad idea; right? You should run app.py instead :)")

from copy import copy
from inspect import isclass
from .utils import ConnectionSingleton
from mysql.connector.cursor import CursorBase
from resources.init import foreignkey_relationships
from mysql.connector.connection import MySQLConnection
from resources.enums import FieldTypes, DatabaseLocations
from resources.exceptions import AbstractInstantiationError
from typing import Any, Union, ItemsView, ValuesView, Type, NamedTuple, Callable


class Q:
    _conditions: list[dict[str, Any], ...] = None

    def __init__(self, **conditions) -> None:
        if not conditions:
            raise ValueError("No conditions specified for Q() instance")
        self._conditions = [conditions]
        super().__init__()

    def __or__(self, other: 'Q'):
        if not isinstance(other, Q):
            raise TypeError("OR with Q() instances, can only be done with other Q() instances.")
        self._conditions += other._conditions

    def __and__(self, other):
        if not isinstance(other, Q):
            raise TypeError("OR with Q() instances, can only be done with other Q() instances.")
        self._conditions[-1] |= {key:val for d in other._conditions for key,val in d.items()}


class QuerySet:
    """
    Django'esque queryet class which allows for retrieving a list of models from the database.
    Currently only able to retrieve all rows of a table.
    """
    model: 'DBModel' = None
    _result: tuple['DBModel', ...] = None
    _filter: str = None
    _values: list[str] = None

    def __init__(self, model) -> None:
        """
        :param model: Hints at to which table should be queried.
        """
        super().__init__()
        self.model: Type[DBModel] = model
        self._result: list[DBModel] = []  # Ensure the list is an instance variable

    def evaluate(self):
        """ Performs the query and caches the result. """

        connection = self.model.meta.connection.connection
        cursor = self.model.meta.connection.cursor

        try: connection.consume_results()
        except Exception: pass

        current_table: str = self.model.meta.table_name
        sql = f"SELECT * FROM {self.model.meta.database_name}.{current_table}"
        if self._filter:
            sql += f"WHERE {self._filter}"

        cursor.execute(f"SELECT * FROM {self.model.meta.database_name}.{current_table} {self._filter}")

        buffer = *(i for i in cursor),  # Buffer needed for certain tables for some reason.
        self._result = *(Models[current_table](obj) for obj in buffer),
        return self

    def filter(self, **kwargs):
        if not kwargs:
            raise ValueError("No conditions specified for QuerySet.filter")

        connection = self.model.meta.connection.connection
        cursor = self.model.meta.connection.cursor

        try: connection.consume_results()
        except Exception: pass

        # Format kwargs for query
        for arg, value in kwargs.items():  # TODO Kevin: Maybe check for SQL injection here, also should probably use _sql_value_formatter()
            if isinstance(value, str):  # Strings should be quoted
                kwargs[arg] = f"\'{value}\'"

        def _init_values(row: tuple[Any, ...]) -> DBModel:
            """ Also set the primary key for model instances retrieved from the database. """
            obj = self.model(*(row[1:]))
            obj._pk = row[0]
            return obj

        cursor.execute(f"SELECT * FROM {self.model.meta.database_name}.{self.model.meta.table_name} WHERE {'AND'.join(('{} = {}'.format(key, value) for key, value in kwargs.items()))}")
        self._result: list[Any] = [_init_values(obj) for obj in cursor]
        return self

    def get(self, **kwargs):

        self.filter(**kwargs)

        if len(self._result) < 1:
            raise LookupError("Get did not return any results.")
        elif len(self._result) > 1:
            raise LookupError("Get returned more than one result.")

        return self._result[0]

    def __iter__(self):
        if self._result is None:
            self.evaluate()
        for instance in self._result:
            yield instance

    def __len__(self):
        if self._result is None:
            self.evaluate()
        return len(self._result)

    def __getitem__(self, item):
        if self._result is None:
            self.evaluate()
        return self._result[item]

    def create(self, **kwargs):
        """ Creates an instance of the specified model, saves it to the database, and returns it to the user. """
        raise NotImplementedError("Create is not finished yet :(")
        invalid_field = next((field for field in kwargs.keys() if field not in self.model.values.keys()), None)
        if invalid_field: raise AttributeError(f"{invalid_field} is not a valid field for {self.model}.")

        # Check for NOT NULL fields that arent specified.
        missing_required = next((field.name for field in self.model.Meta.fields if field.attrs[1] == 'NO' and field.type != 'PRI' and field.name not in kwargs.keys()), None)
        if missing_required: raise AttributeError(f"Cannot create {self.model} object without a value for {missing_required}.")

        instance = self.model(**kwargs)  # Create the instance before we save it.
        instance.save()  # TODO Kevin: Get the primary key from the database when done.

    def __str__(self) -> str:
        return f"{self.__class__.__name__} object of {self.model.__name__}"


class ModelField:
    """ Represents metadata for a column in the database, holds its name and other attributes. """
    name: str = None
    byte_type: bytes = None  # Holds something about the byte type of this field.
    no: str = None  # No idea what this means as of yet.
    type: str = None  # Describes whether this field is a foreignkey, primary key or neither.
    attrs: tuple = None  # A tuple of additional metadata.

    def __init__(self, column: tuple) -> None:
        super().__init__()
        self.name, self.byte_type, self.no, self.type, *self.attrs = column

    def __str__(self) -> str: return self.name


Models: dict[str, Type["DBModel"]] = {}


class LazygetterWrapper(property):
    model: 'DBModel'

    def __init__(self, fk_model: 'DBModel', fget: Callable[[Any], Any] | None = ..., fset: Callable[[Any, Any], None] | None = ...,
                 fdel: Callable[[Any], None] | None = ..., doc: str | None = ...) -> None:
        self.model = fk_model
        super().__init__(fget, fset, fdel, doc)


class _DBModelMeta(type):
    """
    Black magic metaclass; which in our case allows us to specify properties,
    that are provided classes instead of instances when called on classes themselves.
    """

    def __new__(cls, name: str, bases: tuple, dct: dict) -> '_DBModelMeta':

        try:  # Guard clause, do not run for DBModel itself.
            DBModel
        except NameError:
            return super().__new__(cls, name, bases, dct)

        # Create lazy getters for foreignkey fields
        for field, value in dct.items():
            fk_model: Type[DBModel] = None
            if isclass(value) and issubclass(value, DBModel):
                fk_model = value
            elif dct.get('__annotations__', {}).get(field, None) is DBModel and isinstance(value, str):
                fk_model = Models[value]
            # elif # TODO Kevin: Check for ForeignkeyField here

            if fk_model:
                def lazy_foreignkey_getter(self):
                    if isinstance(self._fk_cache.get(field, None), int):  # TODO Kevin: Is None the right way to do this?  # This row has not been queried yet
                        fk_names = foreignkey_relationships[self.meta.table_name][fk_model.meta.table_name + 'ID']

                        # fk_names[1] == name of the PK column on the foreignkey model
                        # self._fk_cache[field] == currently the PK of the foreignkey instance
                        self._fk_cache[field] = fk_model.objects.get(**{fk_names[1]: self._fk_cache[field]})
                    return self._fk_cache.get(field, None)

                def foreignkey_setter(self, val: Any):
                    if isinstance(val, DBModel):
                        self._fk_cache[field] = val.pk
                    elif isinstance(val, (int, NoneType)):
                        self._fk_cache[field] = val
                    else:
                        raise TypeError(f"Cannot assign foreign key field from {type(value)}")

                dct[field] = LazygetterWrapper(fk_model, lazy_foreignkey_getter, foreignkey_setter)

        return super().__new__(cls, name, bases, dct)

    def __init__(cls, name: str, bases: tuple, dct: dict) -> None:
        try:
            if DBModel is not None:  # meta __init__ is also called for DBModel, which is not a database table.
                Models[name] = cls  # TODO Kevin: This will break if we allow class and tables names to differ.

        except NameError:
            pass  # This will be called on DBModel itself, before it is defined.
        super().__init__(cls)

    @property
    def objects(cls) -> QuerySet:
        """ :return: A lazy queryset which may be altered before eventually being evaluated when iterated over (for example). """
        # Metaclassing somehow makes the subclass itself be passed as an argument,
        # which we forward to the queryset constructor.
        return QuerySet(cls)


class ModelMeta(NamedTuple):
    pk_column: str  # TODO Kevin: Dunno if I should keep this
    table_name: str
    database_name: str
    fields: dict[str, Any]
    connection: ConnectionSingleton = None

    def __str__(self) -> str:
        return f"Meta for {self.table_name}"


class DBModel(metaclass=_DBModelMeta):
    """ Django'esque model class which converts table rows to Python class instances. """

    model = None
    # values: dict[str, Any] = None  # Holds the values of the instances.
    _initial_values: dict[str, Any] = None  # Holds the initial values for comparison when saving.
    _fk_cache: dict[str, int]  # TODO Kevin: Put PKs in this when querying
    meta: ModelMeta = None  # Class variable describing the model
    _pk: int = None  # Contains the actual PK  # TODO Kevin: Would prefer if this was not hardcoded to an int.

    def __init__(self, *args, zipped_data: zip = None, **kwargs) -> None:
        """
        Accepts multiple ways to pass model instance data. Use either: args, zipped_data or kwargs when
        constructing instances of DBModel subclasses.
        :param args: Positional arguments that should be ordered in accordance with the fields and their order.
        :param zipped_data: A zip object which pairs field names with their values.
        :param kwargs: Keyword arguments that pairs field names with their values.
        """

        if type(self) is DBModel:  # NOTE Abstraction: This exception prevents creation of instances of the base class.
            raise AbstractInstantiationError("Cannot instantiate instances of DBModel itself, use subclasses instead.")

        # Allow a more readable way to access the class itself from its instances.
        self.model: Type[DBModel] = self.__class__

        self._fk_cache = {}

        # We allow several different ways to pass data to the constructor of the model instance
        if kwargs:
            invalid_field = next((field for field in kwargs.keys() if field not in {metafield.name for metafield in self.Meta.fields}), None)
            if invalid_field: raise AttributeError(f"{invalid_field} is not a valid field for {self.model}")
            self._initial_values = kwargs

            for field, value in kwargs.items():
                setattr(self, field, value)

        else:
            # Zip the data correctly, such that we pair column names with their values.
            data = zipped_data or zip(self.meta.fields.keys(), args) or {field: None for field in self.meta.fields.keys()}
            # Convert the result to a dictionary.
            datadict = {fieldname: value for fieldname, value in data}

            # Take care that we don't set invalid fields for the instance.
            invalid_fields = set(datadict.keys()).difference(set(self.meta.fields.keys()))
            if invalid_fields: raise AttributeError(f"{invalid_fields} are not valid fields for {self.model}")

            for field, value in datadict.items():
                setattr(self, field, value)

            # Merge the values into the class.
            self._initial_values = datadict

        # We run these assignments sequentially,
        # to ensure that the primary key is removed from the dictionary, before it is copied.
        #self._initial_values = copy(values)

        super().__init__()

    @property
    def pk(self) -> int:
        """ Returns the value of the current instance's primary key. """
        return self._pk

    def save(self) -> None:  # TODO Kevin: Test save.
        """ Saves or updates the current instance in the database. """
        # raise NotImplementedError("Save method is currently not finished.")
        cursor = self.meta.connection.cursor

        def _sql_value_formatter(fieldname: str) -> str:
            print(str(getattr(self, fieldname)))
            if isinstance(self.meta.fields[fieldname], LazygetterWrapper):
                instance = getattr(self, fieldname)
                if instance is not None:  # Foreign keys must be saved  # TODO Kevin: Don't like to do this here
                    instance.save()
                    return str(instance.pk)
                else:
                    return 'null'
            elif isinstance(self.meta.fields[fieldname], (StringField, str)):  # TODO Kevin: The type tuple should probably be handled differently.
                return f"'{getattr(self, fieldname)}'"
            return str(getattr(self, fieldname))

        if self.pk:  # Update existing row
            # TODO Kevin: Runtime reflection here; please fix next patch. Also just terrible
            diff = {fieldname: val for fieldname in self.meta.fields.keys() if (val := getattr(self, fieldname)) != self._initial_values[fieldname]}
            values = str(tuple(f"{column} = |||{value}|||" for column, value in diff.items()))[1:-2].replace(r"'",'').replace('|||', r"'")
            cursor.execute(f"UPDATE {self.meta.table_name} SET {values} WHERE {self.meta.pk_column} = {self.pk}")
            self.meta.connection.connection.commit()
        else:  # Insert new row
            # TODO Kevin: Runtime reflection here; please fix next patch. Also just terrible
            valdict = {fieldtype.model.meta.pk_column if isinstance(fieldtype, LazygetterWrapper) else fieldname: _sql_value_formatter(fieldname) for fieldname, fieldtype in self.meta.fields.items()}
            # TODO Kevin: LOCK TABLE '{self.meta.table_name}'
            cursor.execute(f"INSERT INTO {self.meta.table_name}({', '.join(valdict.keys())}) VALUES ({', '.join(valdict.values())})")
            self.meta.connection.connection.commit()

            # Get our PK
            cursor.execute(f"SELECT MAX({self.meta.pk_column}) FROM {self.meta.table_name}")
            # TODO Kevin: UNLOCK TABLES
            self._pk = next(cursor)[0]

    def delete(self):
        self.meta.connection.cursor.execute(f"DELETE FROM {self.meta.table_name} WHERE {self.meta.pk_column} = {self.pk}")
        self.meta.connection.connection.commit()
        self._pk = None  # TODO Kevin: Would break for multiple object for the same row.

    def __str__(self) -> str:
        """ :return: The class name paired with its primary key, when referring to an instance. Otherwise returns super. """
        return f"{self.__class__.__name__} object ({self.pk})" if self.pk else super(DBModel, self).__str__()

    def __eq__(self, o: object) -> bool:
        try:
            return self.meta.table_name == o.meta.table_name and self.pk == o.pk and self.values == o.values
        except AttributeError:
            return False



