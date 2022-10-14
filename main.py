from mysql import connector
from getpass import getpass
from models import User, NotSQLGroup
from argparse import ArgumentParser, Namespace
from resources.init import connect_orm, create_tables
from resources.utils import ConnectionSingleton


def get_options() -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--name', required=True, default='myqueryorm')
    parser.add_argument('-p', '--password', default=None)
    parser.add_argument('-c', '--create', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    options = get_options()
    db_name = options.name
    db_password = options.password
    with connector.connect(host='localhost', user='root', passwd=(db_password or getpass('Password: '))) as mysql_connection:
        with mysql_connection.cursor() as cursor:
            connection = ConnectionSingleton(mysql_connection, cursor)
            create_tables(connection, db_name)
            connect_orm(connection, db_name)

            new_user = User()
            new_user.name = 'hejmeddig'
            new_user.age = 3
            new_user.save()

            try:
                db_user: User = User.objects.get(UserID=3)
            except Exception:
                exit()
            print(db_user.name, db_user.age)
            db_user.name += '2'
            db_user.age += 1
            db_user.save()
            print(db_user.name, db_user.age)

            db_user.delete()
            db_user: User = User.objects.get(UserID=3)


