from mysql import connector
from getpass import getpass
from models import User, Group
from argparse import ArgumentParser, Namespace
from resources.orm import init_orm


def get_options() -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--name', required=True)
    parser.add_argument('-c', '--create', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    options = get_options()
    with connector.connect(host='localhost', user='root', passwd=getpass('password: ')) as connection:
        init_orm(connection.cursor(), 'myqueryorm')
