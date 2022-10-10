from mysql import connector
from getpass import getpass
from models import User, NotSQLGroup
from argparse import ArgumentParser, Namespace
from resources.init import connect_orm, create_tables


def get_options() -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--name', required=True, default='myqueryorm')
    parser.add_argument('-c', '--create', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    options = get_options()
    db_name = options.name
    with connector.connect(host='localhost', user='root', passwd=getpass('Password: ')) as connection:
        with connection.cursor() as cursor:
            create_tables(cursor, db_name)
            # connect_orm(connection.cursor(), db_name)
