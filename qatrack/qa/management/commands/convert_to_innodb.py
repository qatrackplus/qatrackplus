from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    def handle(self, database='default', *args, **options):
        cursor = connections[database].cursor()

        cursor.execute('SHOW TABLE STATUS')

        for row in cursor.fetchall():
            if row[1] != 'InnoDB':
                print(f'Converting {row[0]}', end='')
                result = cursor.execute(f'ALTER TABLE {row[0]} ENGINE=INNODB')
                print(result)
