import threading
import sqlite3
from contextlib import closing
import bitcoin
from bitcoin.rpc import Proxy
from decimal import Decimal, getcontext, ROUND_DOWN, FloatOperation
import walletdb
from time import sleep
import logging.config
import threading

TABLENAME = "sync"
COLUMN_ID = 'id'
COLUMN_BLOCKCOUNT = 'blockcount'

DURATION = 60
CONFIRMATIONS = 6
CHECKPOINT = 125437

BLOCK_KEY_TX = "tx"
TRANSACTION_KEY_AMOUNT = "amount"
TRANSACTION_KEY_DETAILS = "details"
TRANSACTION_KEY_CATEGORY = "category"
TRANSACTION_KEY_ADDRESS = "address"

TRANSACTION_VALUE_CATEGORY_RECEIVE = "receive"

class CWalletSyncher :
    def __init__(self, dbname, dbaccessor, lock):
        self.dbname = dbname
        self.dbaccessor = dbaccessor
        self.dblock = lock
        self._create_table()

        self.logger = logging.getLogger("sync")

        self.stopped = False
        t = threading.Thread(target=self._sync)
        t.start()

    def stop_sync(self):
        self.stopped = True

    def _sync(self) :
        while True:
            self._sync_block()
            if self.stopped:
                break
            sleep(DURATION)

    def _sync_block(self):
        p = Proxy()
        blockcount = p.getblockcount()
        print("sync blockcount = " + str(blockcount))

        with closing(sqlite3.connect(self.dbname)) as connection:
            cursor = connection.cursor()

            checkedcount = self._get_checked_count(cursor)
            print("sync checkedcount = " + str(checkedcount))

            if checkedcount < CHECKPOINT:
                checkedcount = CHECKPOINT

            lastblock = blockcount - CONFIRMATIONS
            if lastblock <= 0:
                return

            for i in range(checkedcount + 1, blockcount - CONFIRMATIONS):
                if self.stopped:
                    break

                print("sync blockheight = " + str(i))
                block = p.getblockbynumber(i)
                if block is None:
                    continue
                if BLOCK_KEY_TX not in block.keys():
                    continue

                for transactionid in block[BLOCK_KEY_TX]:
                    transaction = p.gettransaction(transactionid)

                    if transaction is None:
                        continue

                    if TRANSACTION_KEY_AMOUNT not in transaction.keys():
                        continue

                    amount = transaction[TRANSACTION_KEY_AMOUNT]
                    if amount <= 0:
                        print("sync amount div")
                        continue
                    amount = CWalletSyncher._str_round_down8(amount)
                    print("sync amount = " + amount)

                    if TRANSACTION_KEY_DETAILS not in transaction.keys():
                        print("sync dont have details!!")
                        continue

                    print("sync found receive!!")
                    details = transaction[TRANSACTION_KEY_DETAILS]
                    for detail in details:
                        category = detail[TRANSACTION_KEY_CATEGORY]
                        if (category != TRANSACTION_VALUE_CATEGORY_RECEIVE):
                            continue

                        address = detail[TRANSACTION_KEY_ADDRESS]

                        print("sync receive address = " + address)
                        with self.dblock:
                            row = self.dbaccessor.get_user_by_address(
                                cursor, address)
                            if row is not None:
                                height = row[walletdb.WalletNum.LASTSYNCBLOCK.value]
                                print("sync receive username = " +
                                    row[walletdb.WalletNum.USER.value] + " balance = " + row[walletdb.WalletNum.BALANCE.value] +
                                    " height = " + str(row[walletdb.WalletNum.LASTSYNCBLOCK.value]))

                                src_balance = CWalletSyncher._round_down8(
                                    str(row[walletdb.WalletNum.BALANCE.value]))
                                dst_balance = src_balance + \
                                    CWalletSyncher._round_down8(amount)
                                if dst_balance < CWalletSyncher._round_down8("0.0"):
                                    dst_balance = CWalletSyncher._round_down8("0.0")
                                print("sync update balance = " +
                                    str(dst_balance) + " amount = " + amount)
                                if not self.dbaccessor.update_balance_with_blockheight(cursor, row[walletdb.WalletNum.ID.value], dst_balance, i):
                                    print("sync update faild.")
                                    return
                                self.logger.debug(
                                    "username=" + row[walletdb.WalletNum.USER.value] + " before=" + CWalletSyncher._str_round_down8(src_balance) +
                                    " after=" + CWalletSyncher._str_round_down8(dst_balance) + " height=" + str(i))
                        break
                    pass
                self._update_checked_count(cursor, i)
                connection.commit()

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
                + TABLENAME + ' ({0} integer primary key, {1} integer)'.format(
                    COLUMN_ID, COLUMN_BLOCKCOUNT)
            print(create_table)
            cursor.execute(create_table)
            if self._get_checked_count(cursor) is None:
                self._insert_default_checked_count(cursor)
            connection.commit()

    def _insert_default_checked_count(self, cursor):
        sql = 'insert into ' + TABLENAME + ' ({0}, {1}) values (?,?)'.format(
            COLUMN_ID, COLUMN_BLOCKCOUNT)
        cursor.execute(sql, (0, 0))

    def _update_checked_count(self, cursor, count):
        sql = 'update ' + TABLENAME + \
            ' set {0}=? where {1}=?'.format(COLUMN_BLOCKCOUNT, COLUMN_ID)
        cursor.execute(sql, (count, 0))

    def _get_checked_count(self, cursor):
        select_sql = 'select * from ' + TABLENAME
        cursor.execute(select_sql)
        row = cursor.fetchone()
        count = None
        if row is not None:
            count = row[1]
        return count

    @staticmethod
    def _round_down8(value):
        value = Decimal(value).quantize(Decimal('0.00000000'), rounding=ROUND_DOWN)
        return value

    @staticmethod
    def _str_round_down8(value):
        return "{:.8f}".format(value)
