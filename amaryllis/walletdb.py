import sqlite3
# import myserver_test as myserver
from contextlib import closing
from enum import Enum
from datetime import datetime

TABLENAME = 'wallet'

COLUMN_AUTONUM = 'no'
COLUMN_ID = 'id'
COLUMN_USER = 'username'
COLUMN_ADDRESS = 'address'
COLUMN_BALANCE = 'balance'
COLUMN_PENDING = 'pending'
COLUMN_LASTUPDATE = 'lastupdate'
COLUMN_LASTSYNCBLOCK = 'lastsyncblock'


class WalletNum(Enum):
    ID = 0
    USER = 1
    ADDR = 2
    BALANCE = 3
    PENDING = 4
    LASTUPDATE = 5
    LASTSYNCBLOCK = 6


class CWalletDbAccessor:
    def __init__(self, dbname):
        self.dbname = dbname
        self._create_table()

    def _create_table(self):
        with closing(sqlite3.connect(self.dbname)) as connection:
            cursor = connection.cursor()

            # executeメソッドでSQL文を実行する
            # id '449934944785924096'
            # username ironwood@7205のようなユーザ名 : 備考みたいなもの
            # address : selnアドレス : しばらくはdummyアドレス
            # balance : 残高
            # pending : 仮
            create_table = 'create table if not exists ' \
                + TABLENAME + ' ({0} integer primary key, {1} varchar(64), {2} varchar(64), {3} text, {4} text, {5} text, {6} integer)'.format(
                    COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE, COLUMN_LASTSYNCBLOCK)
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

    # exist user True:exist / False:

    def is_exists_userid(self, cursor, userid):
        select_sql = 'select * from ' + TABLENAME + \
            ' where {0}=?'.format(COLUMN_ID)
        cursor.execute(select_sql, (int(userid),))
        if cursor.fetchone() is None:
            return False
        else:
            return True

    # exist user & address pare

    def is_exists_record(self, cursor, userid, user_name, address, balance, pending):
        # --------------------------
        balance = str(balance)
        pending = str(pending)
        # --------------------------
        select_sql = 'select * from ' + TABLENAME + ' where {0}=? and {1}=? and {2}=? and {3}=? and {4}=?'.format(
            COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING)
        # select_sql = 'select * from ' + TABLENAME + ' where id=?'
        cursor.execute(select_sql, (int(userid), user_name,
                                    address, balance, pending))
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
