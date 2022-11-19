import logging
from datetime import datetime
from logging import Handler
from sqlite3 import connect


class SQLiteHandler(Handler):
    def __init__(self, db_file, insert: str):
        super().__init__(logging.INFO)
        self.db_file = db_file
        self.db_file = connect(self.db_file)
        self.db_file.execute('CREATE TABLE IF NOT EXISTS logs (date TEXT,  time TEXT, lvl INTEGER, lvl_name TEXT, msg TEXT, logger TEXT, lineno INTEGER);')

    def emit(self, record):
        """
        Conditionally emit the specified logging record.

        Emission depends on filters which may have been added to the handler.
        Wrap the actual emission of the record with acquisition/release of
        the I/O thread lock. Returns whether the filter passed the record for
        emission.
        """
        self.db_file.executescript(
            'CREATE TABLE IF NOT EXISTS logs (date TEXT, '
            'time TEXT, lvl INTEGER, lvl_name TEXT, msg TEXT, '
            'logger TEXT, lineno INTEGER);'
            'INSERT INTO logs VALUES ("%s", "%s", %s, "%s", "%s", "%s", %s)' % (
                datetime.now().strftime('%A, the %d of %B, %Y'),
                datetime.now().strftime('%I:%M %p'),
                record.levelno,
                record.level,
                record.msg,
                record.name,
                record.lineno
            )
        )
        self.db_file.commit()
        self.db_file.close()
