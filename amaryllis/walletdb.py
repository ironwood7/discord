import sqlite3
# import myserver_test as myserver
from contextlib import closing
from enum import Enum
from datetime import datetime
import time

TABLENAME = 'wallet'
JACKPOT_TABLENAME = 'jackpot'

COLUMN_AUTONUM = 'no'
COLUMN_ID = 'id'
COLUMN_USER = 'username'
COLUMN_ADDRESS = 'address'
COLUMN_BALANCE = 'balance'
COLUMN_PENDING = 'pending'
COLUMN_LASTUPDATE = 'lastupdate'
COLUMN_LASTSYNCBLOCK = 'lastsyncblock'
COLUMN_LASTCOMMENT = 'lastcomment'
COLUMN_ADMIN = 'admin'

JACKPOT_COLUMN_ID = 'id'
JACKPOT_COLUMN_AMOUNT = 'amount'


class WalletNum(Enum):
    ID = 0
    USER = 1
    ADDR = 2
    BALANCE = 3
    PENDING = 4
    LASTUPDATE = 5
    LASTSYNCBLOCK = 6
    LASTCOMMENT = 7
    ADMIN = 8

class CWalletDbAccessor:
    def __init__(self, dbname):
        self.dbname = dbname
        self._create_table()
        self._create_jackpot_table()

    def _create_table(self):
        with closing(sqlite3.connect(self.dbname)) as connection:
            cursor = connection.cursor()

            create_table = 'create table if not exists ' \
                + TABLENAME + ' ({0} integer primary key, {1} varchar(64), {2} varchar(64), {3} text, {4} text, {5} text, {6} integer, {7} integer, {8} integer)'.format(
                    COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE, COLUMN_LASTSYNCBLOCK, COLUMN_LASTCOMMENT, COLUMN_ADMIN)
            print(create_table)
            cursor.execute(create_table)
            connection.commit()

            # syncblockカラムが無かったら作成.
            cursor = connection.execute(
                "pragma table_info({0})".format(TABLENAME))
            columns = cursor.fetchall()

            exist = False
            for column in columns:
                if column[1] == COLUMN_LASTSYNCBLOCK:
                    exist = True

            if not exist:
                connection.execute("alter table {0} add column {1} integer".format(
                    TABLENAME, COLUMN_LASTSYNCBLOCK))

            # lastcommentカラムが無かったら作成.
            exist = False
            for column in columns:
                if column[1] == COLUMN_LASTCOMMENT:
                    exist = True

            if not exist:
                connection.execute("alter table {0} add column {1} integer".format(
                    TABLENAME, COLUMN_LASTCOMMENT))

            # adminカラムが無かったら作成.
            exist = False
            for column in columns:
                if column[1] == COLUMN_ADMIN:
                    exist = True

            if not exist:
                connection.execute("alter table {0} add column {1} integer".format(
                    TABLENAME, COLUMN_ADMIN))

            connection.commit()

    def _create_jackpot_table(self):
        with closing(sqlite3.connect(self.dbname)) as connection:
            cursor = connection.cursor()

            create_table = 'create table if not exists ' \
                + JACKPOT_TABLENAME + ' ({0} integer primary key, {1} integer)'.format(
                    COLUMN_ID, JACKPOT_COLUMN_AMOUNT)
            print(create_table)
            cursor.execute(create_table)
            if self.get_jackpot(cursor) is None:
                self._insert_default_jackpot(cursor)
            connection.commit()

    def insert_user(self, cursor, userid, username, address, balance, pending):

        # --------------------------
        balance = str(balance)
        pending = str(pending)
        # --------------------------

        update = False
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + ' set {0}=?, {1}=?, {2}=?, {3}=?, {4}=? where {5}=?'.format(
                COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE, COLUMN_ID)
            cursor.execute(sql, (username, address, balance,
                                pending, self._getnowtime(), int(userid)))
            update = True
        else:
            sql = 'insert into ' + TABLENAME + ' ({0}, {1}, {2}, {3}, {4}, {5}) values (?,?,?,?,?,?)'.format(
                COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE)
            cursor.execute(sql, (int(userid), username, address,
                                balance, pending, self._getnowtime()))
        return update

    def update_balance(self, cursor, userid, balance):
        update = False
        # --------------------------
        balance = str(balance)
        # --------------------------
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + \
                ' set {0}=?, {1}=? where {2}=?'.format(
                    COLUMN_BALANCE, COLUMN_LASTUPDATE, COLUMN_ID)
            cursor.execute(sql, (balance, self._getnowtime(), int(userid)))
            update = True
        return update

    def update_lastcomment(self, cursor, userid):
        update = False
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + ' set {0}=? where {1}=?'.format(
                    COLUMN_LASTCOMMENT, COLUMN_ID)
            cursor.execute(sql, (time.time(), int(userid)))
            update = True
        return update

    def update_balance_with_blockheight(self, cursor, userid, balance, height):
        update = False
        # --------------------------
        balance = str(balance)
        # --------------------------
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + \
                ' set {0}=?, {1}=?, {2}=? where {3}=?'.format(
                    COLUMN_BALANCE, COLUMN_LASTUPDATE, COLUMN_LASTSYNCBLOCK, COLUMN_ID)
            cursor.execute(sql, (balance, self._getnowtime(), height, int(userid)))
            update = True
        return update

    def update_username(self, cursor, userid, username):
        update = False
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + \
                ' set {0}=?, {1}=? where {2}=?'.format(
                    COLUMN_USER, COLUMN_LASTUPDATE, COLUMN_ID)
            cursor.execute(sql, (username, self._getnowtime(), int(userid)))
            update = True
        return update

    # address更新

    def update_address(self, cursor, userid, address):
        update = False
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + \
                ' set {0}=?, {1}=? where {2}=?'.format(
                    COLUMN_ADDRESS, COLUMN_LASTUPDATE, COLUMN_ID)
            cursor.execute(sql, (address, self._getnowtime(), int(userid)))
            update = True
        return update

    # pending更新

    def update_pending(self, cursor, userid, pending):
        update = False
        # --------------------------
        pending = str(pending)
        # --------------------------
        if self.is_exists_userid(cursor, userid):
            sql = 'update ' + TABLENAME + \
                ' set {0}=?, {1}=? where {2}=?'.format(
                    COLUMN_PENDING, COLUMN_LASTUPDATE, COLUMN_ID)
            cursor.execute(sql, (pending, self._getnowtime(), int(userid)))
            update = True
        return update

    # exist userid True:exist / False:

    def get_user_row(self, cursor, userid):
        select_sql = 'select * from ' + TABLENAME + \
            ' where {0}=?'.format(COLUMN_ID)
        cursor.execute(select_sql, (int(userid),))
        # 見つかったものを返却
        return cursor.fetchone()

    def get_rain_users(self, cursor, exclude, time):
        print("rain " + str(time))
        select_sql = 'select {0} from '.format(COLUMN_ID) + TABLENAME + \
            ' where {0}>=? and {1}<>? and ({2} is null or {2}<>?)'.format(COLUMN_LASTCOMMENT, COLUMN_ID, COLUMN_ADMIN)
        cursor.execute(select_sql, (int(time), exclude, 1))
        return cursor.fetchall()

    # exist user True:exist / False:
    def is_exists_userid(self, cursor, userid):
        select_sql = 'select * from ' + TABLENAME + \
            ' where {0}=?'.format(COLUMN_ID)
        cursor.execute(select_sql, (int(userid),))
        if cursor.fetchone() is None:
            return False
        else:
            return True

    def count_record(self, cursor):
        select_sql = 'select count(*) from ' + TABLENAME
        cursor.execute(select_sql)
        count = cursor.fetchone()
        return count

    def dump_all(self, cursor):
        for row in cursor.execute("select * from " + TABLENAME):
            print(row)

    def _getnowtime(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def get_user_by_address(self, cursor, address):
        select_sql = 'select * from ' + TABLENAME + \
            ' where {0}=?'.format(COLUMN_ADDRESS)
        cursor.execute(select_sql, (address,))
        return cursor.fetchone()

    def set_admin(self, cursor, userid):
        sql = 'update ' + TABLENAME + \
            ' set {0}=? where {1}=?'.format(
                COLUMN_ADMIN, COLUMN_ID)
        cursor.execute(sql, (1, int(userid)))

    def is_admin(self, cursor, userid):
        select_sql = 'select {0} from '.format(COLUMN_ADMIN) + TABLENAME + \
            ' where {0}=?'.format(COLUMN_ID)
        cursor.execute(select_sql, (int(userid),))
        admin_flag = cursor.fetchone()
        if admin_flag is None or admin_flag[0] is None or admin_flag[0] != 1:
            return False
        else:
            return True


    def _insert_default_jackpot(self, cursor):
        sql = 'insert into ' + JACKPOT_TABLENAME + ' ({0}, {1}) values (?,?)'.format(
            JACKPOT_COLUMN_ID, JACKPOT_COLUMN_AMOUNT)
        cursor.execute(sql, (0, 0))

    def update_jackpot(self, cursor, amount):
        sql = 'update ' + JACKPOT_TABLENAME + \
            ' set {0}=? where {1}=?'.format(JACKPOT_COLUMN_AMOUNT, JACKPOT_COLUMN_ID)
        cursor.execute(sql, (amount, 0))

    def add_jackpot(self, cursor, amount):
        sql = 'update ' + JACKPOT_TABLENAME + \
            ' set {0}={0}+? where {1}=?'.format(
                JACKPOT_COLUMN_AMOUNT, JACKPOT_COLUMN_ID)
        cursor.execute(sql, (amount, 0))

    def get_jackpot(self, cursor):
        select_sql = 'select * from ' + JACKPOT_TABLENAME
        cursor.execute(select_sql)
        row = cursor.fetchone()
        amount = None
        if row is not None:
            amount = row[1]
        return amount
