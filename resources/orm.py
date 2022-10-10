"""
Stores database data and queryset models.
"""

if __name__ == '__main__':
    # Gently remind the user to not run program.py themselves
    raise SystemExit("(⊙＿⊙') Wha!?... Are you trying to run orm.py?\n"
                     " You know this is a bad idea; right? You should run app.py instead :)")

from typing import Any, Union, ItemsView, ValuesView, Type, NamedTuple
from mysql.connector.cursor import CursorBase
from mysql.connector.connection import MySQLConnection
try:
    from mysql.connector.cursor_cext import CMySQLCursor
except ImportError:
    # Importation of CMySQLCursor fails on Windows, for some reason.
    CMySQLCursor = None  # Avoid typehint NameError on failed import.
from copy import copy
from resources.enums import FieldTypes, DatabaseLocations
from resources.exceptions import AbstractInstantiationError


class LazyQueryDict(dict):
    """ This dictionary subclass lazily queries related foreignkey rows when retrieved. """
    __instance = None  # instance is private, as it should not be included when values are retrieved.

    def __init__(self, instance, **kwargs) -> None:
        """
        :param instance: The instance of a DBModel subclass that this dictionary is linked to.
        :param kwargs: Keyword arguments passed to the original dictionary constructor.
        """
        super().__init__(**kwargs)
        self.__instance: DBModel = instance

    def __getitem__(self, k: Any) -> Any:
        """
        Checks the value and type of the specified key to determine
        if a query should be performed before the value is returned.

        :param k: the specified key to retrieve the value of.
        """

        # May raise KeyError
        item: Any = super().__getitem__(k)

        if k in self and type(item) is int and next(
                (field for field in self.__instance.Meta.fields if
                 field.type == FieldTypes.FOREIGN_KEY.value and field.name == k), None):
            model = self.__instance.model
            fk_names = _foreignkey_relationships[model.Meta.table_name][k]
            self[k] = item = Models[fk_names[0]].objects.get(**{fk_names[1]: item})

        return item

    def _fetch_all(self) -> None:  # TODO Kevin: Consider whether this method should be converted to an annotation.
        """ Prefetches all contained foreignkeys. """
        for key in self.keys():
            self[key]  # Forces the foreignkey to be evaluated.

    def values(self) -> ValuesView[Any]:
        """ Preemptively evaluates all contained foreignkeys before returning super. """
        self._fetch_all()
        return super().values()

    def items(self) -> ItemsView[str, Any]:
        """ Preemptively evaluates all contained foreignkeys before returning super. """
        self._fetch_all()
        return super().items()


class QuerySet:
    """
    Django'esque queryet class which allows for retrieving a list of models from the database.
    Currently only able to retrieve all rows of a table.
    """
    model = None
    _evaluated = False
    _result: list = None

    def __init__(self, model) -> None:
        """
        :param model: Hints at to which table should be queried.
        """
        super().__init__()
        self.model: Type[DBModel] = model
        self._result: list[DBModel] = []

    def evaluate(self):
        """ Performs the query and caches the result. """
        try: CONNECTION.consume_results()
        except Exception: pass
        current_table: str = self.model.Meta.table_name
        CURSOR.execute(f"SELECT * FROM {DATABASE_NAME}.{current_table}")
        buffer = *(i for i in CURSOR),  # Buffer needed for certain tables for some reason.
        self._result = [Models[current_table](obj) for obj in buffer]
        self._evaluated = True
        return self

    def get(self, **kwargs):
        if not kwargs:
            raise ValueError("No conditions specified for QuerySet.get")

        try: CONNECTION.consume_results()
        except Exception: pass

        current_table: str = self.model.Meta.table_name
        CURSOR.execute(f"SELECT * FROM {DATABASE_NAME}.{current_table} WHERE {'AND'.join(('{} = {}'.format(key, value) for key, value in kwargs.items()))}")
        buffer: list[DBModel] = [Models[current_table](obj) for obj in CURSOR]

        if len(buffer) < 1:
            raise Exception("Get did not return any results.")
        elif len(buffer) > 1:
            raise Exception("Get returned more than one result.")

        self._result, self._evaluated = buffer, True
        return buffer[0]

    def __iter__(self):
        if not self._evaluated: self.evaluate()
        for instance in self._result:
            yield instance

    def __len__(self):
        if not self._evaluated: self.evaluate()
        return len(self._result)

    def create(self, **kwargs):
        """ Creates an instance of the specified model, saves it to the database, and returns it to the user. """
        raise NotImplementedError("Create is not finished yet")
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


Models: set["DBModel"] = set()
_foreignkey_relationships: dict[str, dict[str, tuple[str, str]]] = {}


class _DBModelMeta(type):
    """
    Black magic metaclass; which in our case allows us to specify properties,
    that are provided classes instead of instances when called on classes themselves.
    """

    def __init__(cls, name: str, bases: tuple, dct: dict) -> None:
        try:
            if DBModel is not None:  # meta __init__ is also called for DBModel, which is not a database table.
                Models.add(cls)
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

    def __str__(self) -> str:
        return f"Meta for {self.table_name}"


class DBModel(metaclass=_DBModelMeta):
    """ Django'esque model class which converts table rows to Python class instances. """

    model = None
    values: dict[str, Any] = None  # Holds the values of the instances.
    _initial_values: dict[str, Any] = None  # Holds the initial values for comparison when saving.
    meta: ModelMeta = None

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

        # We allow several different ways to pass data to the constructor of the model instance
        if kwargs:
            invalid_field = next((field for field in kwargs.keys() if field not in {metafield.name for metafield in self.Meta.fields}), None)
            if invalid_field: raise AttributeError(f"{invalid_field} is not a valid field for {self.model}")
            self.values = LazyQueryDict(self, **kwargs)
        else:
            # Zip the data correctly, such that we pair column names with their values.
            data = zipped_data or zip(self.Meta.fieldnames, *args) or {field: None for field in self.Meta.fieldnames}
            # Convert the result to a dictionary.
            datadict = {fieldname: value for fieldname, value in data}

            # Take care that we don't set invalid fields for the instance.
            invalid_fields = set(datadict.keys()).difference(set(self.Meta.fieldnames))
            if invalid_fields: raise AttributeError(f"{invalid_fields} are not valid fields for {self.model}")

            # Merge the values into the class.
            self.values = LazyQueryDict(self, **datadict)

        # We run these assignments sequentially,
        # to ensure that the primary key is removed from the dictionary, before it is copied.
        self._initial_values = copy(self.values)

        super().__init__()

    @property
    def pk(self) -> int:
        """ Returns the value of the current instance's primary key. """
        return self.values.get(self.Meta.pk_column, None)

    def save(self) -> None:  # TODO Kevin: Test save.
        """ Saves or updates the current instance in the database. """
        raise NotImplementedError("Save method is currently not finished.")
        diff = {column: value for column, value in self.values if (value or self._initial_values[column])}
        if self.pk:
            values = str(tuple(f"{column} = |||{value}|||" for column, value in diff.items()))[1:-2].replace(r"'",'').replace('|||', r"'")
            CURSOR.execute(f"UPDATE {self.Meta.table_name} SET {values} WHERE {self.Meta.pk_column} = {self.pk}")
        else:
            columns, values = diff.items()
            CURSOR.execute(f"INSERT INTO {self.Meta.table_name}({columns}) VALUES {values}")

    def delete(self): raise NotImplementedError("Cannot delete yet!")

    def __str__(self) -> str:
        """ :return: The class name paired with its primary key, when referring to an instance. Otherwise returns super. """
        return f"{self.__class__.__name__} object ({self.pk})" if self.pk else super(DBModel, self).__str__()

    def __eq__(self, o: object) -> bool:
        try:
            return self.Meta.table_name == o.Meta.table_name and self.pk == o.pk and self.values == o.values
        except AttributeError:
            return False



