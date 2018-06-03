import discord
import sqlite3
from contextlib import closing

DBNAME = 'database_airdrop.db'
PRE_TABLENAME= 'predrop'
MAX_RECORD = 500

def on_ready():
    _create_tabel()

async def on_message_inner(client, message):
    print("airdrop {0}:{1}".format(message.author, message.content))

    if message.content.startswith(",airdrop"):
        params = message.content.split()
        user = str(message.author)
        if (len(params) < 2):
            await client.send_message(message.channel, "{0}様、申し訳ございません。アドレスがみつけられませんでした".format(user))
            return

        accept = False
        address = str(params[1])
        if (address.startswith("S")):
            if (len(address) == 34):
                with closing(sqlite3.connect(DBNAME)) as connection:
                    cursor = connection.cursor()
                    count = count_record(cursor)
                    if count[0] > MAX_RECORD:
                        await client.send_message(message.channel, "もう業務時間終了いたしましたわ。わたくし多忙ですので話しかけないでくださる？")
                        return
                        
                    update = _insert_user(cursor, user, address)
                    connection.commit()
                    if _is_exists_record(cursor, user, address):
                        if not update:
                            await client.send_message(message.channel, "{0}様、お受付いたしました".format(user))
                        else:
                            await client.send_message(message.channel, "{0}様、アドレスを更新いたしました".format(user))
                        accept = True
                    else:
                        await client.send_message(message.channel, "{0}さま！大変です！し、し、しっぱいいたしました！！！".format(user))
                    
        if (not accept):
            await client.send_message(message.channel, "{0}様、大変申し上げにくいのですがアドレスが不正ではございませんか・・？".format(user))
    else:
        await client.send_message(message.channel, "{0}様、コマンドがあっておりますか・・？".format(user))

def _create_tabel():
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()

        # executeメソッドでSQL文を実行する
        create_table = 'create table if not exists ' \
            + PRE_TABLENAME + ' (id varchar(32), address varchar(64))'
        print(create_table)
        cursor.execute(create_table)
        connection.commit()
    
def _insert_user(cursor, user, address):
    update = False
    if _is_exists_user(cursor, user):
        sql = 'update ' + PRE_TABLENAME + ' set address=? where id=?'
        print(sql)
        cursor.execute(sql, (address, user)) 
        update = True
    else:
        sql = 'insert into ' + PRE_TABLENAME + ' (id, address) values (?,?)'
        print(sql)
        cursor.execute(sql, (user, address))
    return update

def _is_exists_user(cursor, user):
    select_sql = 'select * from ' + PRE_TABLENAME + ' where id=?'
    print(select_sql)
    cursor.execute(select_sql, (user,))
    if cursor.fetchone() is None:
        return False
    else:
        return True

def _is_exists_record(cursor, user, address):
    select_sql = 'select * from ' + PRE_TABLENAME + ' where id=? and address=?'
    print(select_sql)
    cursor.execute(select_sql, (user, address))
    if cursor.fetchone() is None:
        return False
    else:
        return True

def count_record(cursor):
    select_sql = 'select count(*) from ' + PRE_TABLENAME
    print(select_sql)
    cursor.execute(select_sql)
    count = cursor.fetchone()
    print(count)
    return count

def _dump_all(cursor):
    for row in cursor.execute("select * from " + PRE_TABLENAME):
        print(row)
