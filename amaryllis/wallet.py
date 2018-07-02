import discord
import sqlite3
import myserver
from contextlib import closing

cmd_admin_str="ironwood#7205"

# 登録データ
DBNAME = 'database_register.db'
REG_TABLENAME= 'register'
MAX_RECORD = 10000000

def on_ready():
    _create_table()

async def on_message_inner(client, message):
    # dump
    if message.channel.id == myserver.CH_ID_REGISTER:
        await _cmd_dump(client, message)
        await _cmd_register(client, message)
    # dump
    elif message.channel.id == myserver.CH_ID_ADDRESS:
        await _cmd_address(client, message)
        await _cmd_withdraw(client, message)
    elif message.channel.id == myserver.CH_ID_WALLET:
        await _cmd_info(client, message)
        await _cmd_withdraw(client, message)


# @breif ,register ウォレットを作成します。
# @return seln address
async def _cmd_register(client, message):
    if message.content.startswith(",register"):
        print("register {0}:{1}".format(message.author, message.content))
        params = message.content.split()
        user = str(message.author)
        if (len(params) >= 2):
            await client.send_message(message.channel, "{0}様、申し訳ございません。いらない引数があります。".format(user))
            return

        accept = False

        # ユーザ登録を行う前にユーザがいるかどうか確認する.
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            count = count_record(cursor)

            # ユーザが登録済みかを確認する.updateでもう一度読んでしまうが、最初の登録なので、時間待っても問題none
            # むしろwait必要？
            if _is_exists_user(cursor, user):
                # すでにユーザが存在する
                await client.send_message(message.channel, "{0}様、もう登録されておりますよ。".format(user))
                return

            if count[0] > MAX_RECORD:
                await client.send_message(message.channel, "{0}様、もう業務時間終了致しました。".format(user))
                return

        # DB上にユーザがいないことが判明
        # TODO ユーザ登録が無いのでここでselnアドレスを取得しに行く -> RPC
        address = _get_regist_address(user)

        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            count = count_record(cursor)

            # コミット/アドレス上書き(registerにおいては上書きはない)
            update = _insert_user(cursor, user, address)
            connection.commit()


            if _is_exists_record(cursor, user, address):
                if not update:
                    await client.send_message(message.channel, "{0}様、お受付いたしました".format(user))
                else:
                    await client.send_message(message.channel, "{0}様、前のアドレスを喪失してしまいました。".format(user))
                # OK
                accept = True
            else:
                # NG
                await client.send_message(message.channel, "{0}さま！大変です！し、し、しっぱいいたしました！！！".format(user))
        if accept:
            await client.send_message(message.channel, "{0}様のaddressは、{1} となります。".format(user, address))
        return

# @breif ,dump デバッグコマンド。
# @return  user - seln address list
async def _cmd_dump(client, message):
    if message.content.startswith(",dump"):
        user = str(message.author)
        if (user != cmd_admin_str):
            return
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            _dump_all(cursor)
            # await _dump_all_private(client, message, cursor)


# @breif ,address  : wallet Value
# @return xsel Value
async def _cmd_info(client, message):
    if message.content.startswith(",info"):
        # TODO 現在のXSELの価格を表示します。
        value = "0.0000000"
        await client.send_message(message.channel, "{0}".format(value))

# @breif ,address command : wallet address
# @return  seln address
async def _cmd_address(client, message):
    # TODO selnのアドレスを取得します
    if message.content.startswith(",address"):
        print("address {0}:{1}".format(message.author, message.content))
        params = message.content.split()
        user = str(message.author)
        if (len(params) >= 2):
            await client.send_message(message.channel, "{0}様、申し訳ございません。いらない引数があります。".format(user))
            return
        # TODO 現在のXSELの価格を表示します。
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, user)
            # print(row)
            if row is not None:
                await client.send_message(message.channel, str(row[1]))
            else:
                await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user))


# @breif ,withdraw (addr) (amount) : withdraw
# @return  user - seln address list
async def _cmd_withdraw(client, message):
    # TODO 「addr」に対して、「amount」XSELを送金します。
    pass

# @breif ,balance : wallet balance
# @return wallet balance
async def _cmd_balance(client, message):
    # TODO ウォレットの残高を確認します。
    pass


# @breif ,tip (to) (amount) : tips (default 1xsel)
# @return wallet balance
async def _cmd_tip(client, message):
    # TODO 「to」に対して、「amount」XSELを渡します。 toには、discordの名前を指定してください。
    # 例：,tip seln#xxxx 3
    pass

# @breif ,rain (amount) present
# @return  user - seln address list
async def _cmd_rain(client, message):
    # TODO オフラインではない人で、挿入金額が5XSELの人にXSELを均等にプレゼント。

    # -- 暫定仕様 --
    # 実装としてはdbのユーザからオンラインリストを作成
    # オンラインリストから条件合致したものをフィルタ
    # 確定したリストに対して送信
    pass

##########################################
# Utility
##########################################

def _create_table():
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()

        # executeメソッドでSQL文を実行する
        create_table = 'create table if not exists ' \
            + REG_TABLENAME + ' (id varchar(32), address varchar(64))'
        print(create_table)
        cursor.execute(create_table)
        connection.commit()

# insert_user
def _insert_user(cursor, user, address):
    update = False
    if _is_exists_user(cursor, user):
        sql = 'update ' + REG_TABLENAME + ' set address=? where id=?'
        print(sql)
        cursor.execute(sql, (address, user)) 
        update = True
    else:
        sql = 'insert into ' + REG_TABLENAME + ' (id, address) values (?,?)'
        print(sql)
        cursor.execute(sql, (user, address))
    return update

# exist user True:exist / False:
def _get_user_row(cursor, user):
    select_sql = 'select * from ' + REG_TABLENAME + ' where id=?'
    print(select_sql)
    cursor.execute(select_sql, (user,))
    return cursor.fetchone()

# exist user True:exist / False:
def _is_exists_user(cursor, user):
    select_sql = 'select * from ' + REG_TABLENAME + ' where id=?'
    print(select_sql)
    cursor.execute(select_sql, (user,))
    if cursor.fetchone() is None:
        return False
    else:
        return True

# exist user & address pare
def _is_exists_record(cursor, user, address):
    select_sql = 'select * from ' + REG_TABLENAME + ' where id=? and address=?'
    print(select_sql)
    cursor.execute(select_sql, (user, address))
    if cursor.fetchone() is None:
        return False
    else:
        return True

def count_record(cursor):
    select_sql = 'select count(*) from ' + REG_TABLENAME
    print(select_sql)
    cursor.execute(select_sql)
    count = cursor.fetchone()
    print(count)
    return count

def _dump_all(cursor):
    for row in cursor.execute("select * from " + REG_TABLENAME):
        print(row)

# debug private msg print
# async def _dump_all_private(client, message, cursor):
#     for row in cursor.execute("select * from " + REG_TABLENAME):
#         await client.send_message(message.author,str(row))

# RPCでアドレスを作成する依頼を出す。
def _get_regist_address(user):
    # TODO ここでRPC経由でアドレスを取得する。
    return "Sxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"



