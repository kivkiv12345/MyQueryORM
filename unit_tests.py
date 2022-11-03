"""
Run this module to perform the preconfigured unit tests for MyQueryHouse.
"""

import docker
import unittest
from time import sleep
from typing import Type
from os.path import join

from resources.modelfields import StringField
from resources.orm import DBModel
from mysql.connector import connect
from resources.init import create_tables
from mockmodels import User, NotSQLGroup
from subprocess import call, DEVNULL, run
from mysql.connector import MySQLConnection
from docker.errors import NotFound, APIError
from mysql.connector.cursor import CursorBase
from docker.models.containers import Container
from resources.utils import ConnectionSingleton
from test_resources.utils import TempDockerContainer
from test_resources.test_subclass import MoreTestCases
from resources.exceptions import AbstractInstantiationError


DATABASE_NAME = 'MyQueryORM_Mock'


class TestOrm(MoreTestCases):
    connection_singleton: ConnectionSingleton
    container: Container

    def setUp(self):
        """ Instantiates a MySQL Docker container mock database, to run unit tests against. """

        # TODO Kevin: Some refactoring may be in order here. Destruction of unit test resources raises ResourceWarning;
        #   stating: unclosed socket. This may hint at needed changes to an __exit__ method somewhere.

        client = docker.from_env()
        client.images.pull('mysql')  # Ensure that the image is pulled.

        CONTAINER_NAME = DATABASE_NAME + '_test_db'
        PASSWORD = "Test1234!"
        PORT = 53063

        try:  # Attempt to retrieve an existing testing container.
            container = client.containers.get(CONTAINER_NAME)
        except NotFound:  # Create one for our use case.
            container = client.containers.run(
                'mysql',
                name=CONTAINER_NAME,
                environment=[f"MYSQL_ROOT_PASSWORD={PASSWORD}"],
                ports={"3306/tcp": PORT},
                detach=True,
                auto_remove=True
            )

        if not container.attrs['State']['Running']:
            print(f"Waiting for container with name: '{container.name}' to start.")
            sleep(15)

        connection = connect(
            host='127.0.0.1',
            user='root',
            port=PORT,
            password=PASSWORD,
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}")

        self.container = container
        self.connection_singleton = ConnectionSingleton(connection, cursor)

        create_tables(self.connection_singleton, DATABASE_NAME)

    def tearDown(self) -> None:
        """ Stop and delete created Docker container. """
        self.connection_singleton.cursor.close()
        self.connection_singleton.connection.close()
        try:
            self.container.stop()
            self.container.remove()
        except (NotFound, APIError):
            pass  # Container is most likely already deleted, happens when the container has auto_remove set to True.

    def test_dbmodel(self):
        """ Check that instantiating DBModels raises an AbstractInstantiationError. """
        with self.assertRaises(AbstractInstantiationError):
            DBModel()

    def test_createuser(self):

        # Setup phase
        user = User()
        user.name = 'Trololo'
        user.save()

        with self.assertNotRaises(LookupError):
            db_user = User.objects.get(name='Trololo')  # Check that we can query the user we created.
            self.assertEqual(db_user.name, 'Trololo')  # Check that the name is applied correctly.


if __name__ == '__main__':
    unittest.main()
