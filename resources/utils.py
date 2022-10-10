"""
This module holds the utility methods and classes used by MyQueryHouse.
"""

if __name__ == '__main__':
    raise SystemExit("Cannot run utils.py")

import os
from resources import orm
from subprocess import run, DEVNULL
from mysql.connector import ProgrammingError
from resources.enums import DatabaseLocations
from resources.orm import QuerySet, DATABASE_NAME


def restore_database(logindeets:dict, filename=DATABASE_NAME + '.sql', container_name:str = None) -> None:
    """
    Looks for a file in 'database_backups/', and uses it to restore the database on the server.

    :param logindeets: Dictionary of login details, used to connect to the database server.
    :param filename: The name of the .sql file in 'database_backups/' to use.
    :param container_name: The name of the container the database is located in, only applicable when using Docker.
    """

    restore_db_args = () if orm.database_location is DatabaseLocations.DOCKER else ('-h', logindeets['host'])

    try:
        with open(os.path.join("database_backups", "filename")) as db_file:
            # The following command populates the database according to the opened .sql file.
            command = ["mysql", DATABASE_NAME, "-u", "root", f"--password={logindeets['passwd']}", *restore_db_args]
            if orm.database_location is DatabaseLocations.DOCKER:  # Execute inside the docker container, if applicable.
                assert container_name, "Container name must be specified when using Docker"
                command = ["docker", "exec", "-i", container_name] + command
            run(command, stdin=db_file, stdout=DEVNULL, stderr=DEVNULL)

            try:  # The above command currently fails on Linux, and this one requires that MySQL-client is installed.
                command = ["mysql", DATABASE_NAME, "-u", "root", f"--password={logindeets['passwd']}", "-h", "127.0.0.1", "-P", str(logindeets['port'])]
                run(command, stdin=db_file, stdout=DEVNULL, stderr=DEVNULL)
            except Exception:  # Fails when the MySQL-client is not installed.
                pass

    except ProgrammingError as e:
        print(f"Failed to restore database from {filename}; stating: '{e}',\ndoes the file exist?")
