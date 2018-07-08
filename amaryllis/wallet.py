import discord
import sqlite3
import myserver
from contextlib import closing
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException


cmd_admin_str="ironwood#7205"
WITHDRAW_AMOUNT_MAX = 10
TIP_AMOUNT_MAX      = 4
RAIN_AMOUNT_MAX     = 1

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
        await _cmd_balance(client, message)
        await _cmd_tip(client, message)
        await _cmd_rain(client, message)
    
    await _cmd_dbg_info(client, message)
    return

# @breif ,register ウォレットを作成します。
# @return seln address
async def _cmd_register(client, message):
    if message.content.startswith(",register"):
        # param get
        print("register {0}:{1}".format(message.author, message.content))
        params = message.content.split()
        user = str(message.author)
        user_mention = message.author.mention

        if (len(params) >= 2):
            await client.send_message(message.channel, "{0}様、申し訳ございません。いらない引数があります。".format(user_mention))
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
                await client.send_message(message.channel, "{0}様、もう登録されておりますよ。".format(user_mention))
                return

            if count[0] > MAX_RECORD:
                await client.send_message(message.channel, "{0}様、もう業務時間終了致しました。".format(user_mention))
                return

        # DB上にユーザがいないことが判明
        ##############################
        # TODO ユーザ登録が無いのでここでselnアドレスを取得しに行く -> RPC
        ##############################
        address = _get_regist_address(user)

        ##############################

        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            count = count_record(cursor)

            # コミット/アドレス上書き(registerにおいては上書きはない)
            update = _insert_user(cursor, user, address)
            connection.commit()


            if _is_exists_record(cursor, user, address):
                if not update:
                    await client.send_message(message.channel, "{0}様、お受付いたしました".format(user_mention))
                else:
                    await client.send_message(message.channel, "{0}様、前のアドレスを喪失してしまいました。".format(user_mention))
                # OK
                accept = True
            else:
                # NG
                await client.send_message(message.channel, "{0}さま！大変です！し、し、しっぱいいたしました！！！".format(user_mention))
        if accept:
            ################################
            rg_user  = "**所有者**\r\n{0} 様  \r\n".format(user)
            rg_src   = "**アドレス**\r\n{0}   \r\n".format(address)
            disp_msg = rg_user +rg_src
            await _disp_rep_msg( client, message,'登録情報','',disp_msg )
            ################################


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
        ################################
        # TODO 現在のXSELの価格を表示します。selndに問い合わせ
        ################################

        value = "0.0000000"
        ################################
        ad_user = "**価格**\r\n{0}   \r\n".format(value)
        # 見づらいので分解(遅くなるけど無視)
        disp_msg = ad_user
        await _disp_rep_msg( client, message,'XSELの価格','',disp_msg )
        ################################
    return

# @breif ,address command : wallet address
# @return  seln address
async def _cmd_address(client, message):
    # selnのアドレスを取得します
    if message.content.startswith(",address"):
        print("address {0}:{1}".format(message.author, message.content))
        params       = message.content.split()
        user         = str(message.author)
        user_mention = message.author.mention

        if (len(params) >= 2):
            await client.send_message(message.channel, "{0}様、申し訳ございません。いらない引数があります。".format(user_mention))
            return
        # user でDBからaddr取得

        src_addr = None
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, user)
            # print(row)
            if row is not None:
                src_addr = str(row[1])
            else:
                await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
                return

        ################################
        ad_user = "**所有者**\r\n{0} 様  \r\n".format(user)
        ad_src  = "**アドレス**\r\n{0}     \r\n".format(src_addr)
        # 見づらいので分解(遅くなるけど無視)
        disp_msg = ad_user +ad_src
        await _disp_rep_msg( client, message,'登録情報','',disp_msg )
        ################################
    return


# @breif ,balance : wallet balance
# @return wallet balance
async def _cmd_balance(client, message):
    # ウォレットの残高を確認します。
    if message.content.startswith(",balance"):
        # userからaddressを取得する。
        print("withdraw {0}:{1}".format(message.author, message.content))
        params       = message.content.split()
        user         = str(message.author)
        user_mention = message.author.mention

        src_addr = ""
        if (len(params) > 1):
            await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが余計です。".format(user_mention))
            return

        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, user)
            if row is not None:
                # src アドレス取得
                src_addr = str(row[1])
            else:
                await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
                return

        ################################
        # TODO このアドレス:src_addrにてRPC経由で財布を確認
        ################################
        # getaccount src_addr
        # getbalance [account] [minconf=1]
        # 見づらいので分解(遅くなるけど無視)
        bl_user     = "**所有者**\r\n{0} 様  \r\n".format(user)
        bl_result   = "**残高**\r\n{0} XSEL  \r\n".format(400.10012190)
        bl_veri_end = "**検証済**\r\n{0} XSEL\r\n".format(400.10012190)
        bl_veri_dur = "**検証中**\r\n{0} XSEL\r\n".format(0.000000)
        bl_veri_non = "**未検証**\r\n{0} XSEL\r\n".format(0.000000)

        disp_msg = bl_user +bl_result +bl_veri_end +bl_veri_dur +bl_veri_non

        await _disp_rep_msg( client, message,'残高(BALANCE)','検証分のみ表示されます。',disp_msg )
        ################################
    return


# @breif ,withdraw (addr) (amount) : withdraw
# @return  user - seln address list
async def _cmd_withdraw(client, message):
    # 「addr」に対して、「amount」XSELを送金します。
    if message.content.startswith(",withdraw"):
        # 引数からdstaddressを取得する。
        # ユーザからsrcaddressを取得する。
        print("withdraw {0}:{1}".format(message.author, message.content))
        params = message.content.split()
        user = str(message.author)
        src_addr = ""
        dst_addr = ""
        if (len(params) != 3):
            await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが間違えています。".format(user_mention))
            return
        if False == params[2].isdigit():
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, params[2]))
            return
        amount = 0
        try:
            dst_addr = params[1]
            amount   = int(params[2])
        except:
            # exceptionで戻る
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
            return

        # amount制限
        if amount > WITHDRAW_AMOUNT_MAX:
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが上限を超えています。".format(user_mention, amount))
            return

        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, user)
            if row is not None:
                # src アドレス取得
                src_addr = str(row[1])
            else:
                await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
                return

        ################################
        # TODO ここでRPCにて送金依頼
        ################################
        # src_addr,dst_addr,amount

        ################################
        wd_user = "**所有者**\r\n{0} 様  \r\n".format(user)
        wd_src  = "**送信元**\r\n{0}     \r\n".format(src_addr)
        wd_dst  = "**送信先**\r\n{0}     \r\n".format(dst_addr)
        wd_am   = "**送金額**\r\n{0} XSEL\r\n".format(amount)
        # 見づらいので分解(遅くなるけど無視)
        disp_msg = wd_user +wd_src +wd_dst +wd_am
        await _disp_rep_msg( client, message,'送金(withdraw)','以下のように送金しました。',disp_msg )
        ################################
    return

# @breif ,tip (to) (amount) : tips (default 1xsel)
# @return wallet balance
async def _cmd_tip(client, message):
    # 「to」に対して、「amount」XSELを渡します。 toには、discordの名前を指定してください。
    # 例：,tip seln#xxxx 3
    if message.content.startswith(",tip"):
        # 引数からdstaddressを取得する。
        # ユーザからsrcaddressを取得する。
        print("tip {0}:{1}".format(message.author, message.content))
        params       = message.content.split()
        user         = str(message.author)
        user_mention = message.author.mention


        to_user = ""
        src_addr = ""
        dst_addr = ""
        if (len(params) != 3):
            await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが間違えています。".format(user_mention))
            return
        if False == params[2].isdigit():
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, params[2]))
            return
        amount = 0
        try:
            to_user = params[1]
            amount  = int(params[2])
        except:
            # exceptionで戻る
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
            return

        # amount制限
        if amount > TIP_AMOUNT_MAX:
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが上限を超えています。".format(user_mention, amount))
            return
        # ----------------------------
        # まず自分のアドレス
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, user)
            if row is not None:
                # src アドレス取得
                src_addr = str(row[1])
            else:
                await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
                return
        # ----------------------------
        # 相手のアドレス
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, to_user)
            if row is not None:
                # src アドレス取得
                dst_addr = str(row[1])
            else:
                await client.send_message(message.channel, "{0}様、TO:{1}様のアドレスは登録されていないようです。".format(user_mention, to_user))
                return
        ################################
        # TODO ここでRPCにて送金依頼
        ################################
        # src_addr,dst_addr,amount

        ################################
        tip_user = "**所有者**\r\n{0} 様  \r\n".format(user)
        tip_src  = "**送信元**\r\n{0}     \r\n".format(src_addr)
        tip_dst  = "**送信先**\r\n{0}     \r\n".format(dst_addr)
        tip_am   = "**送金額**\r\n{0} XSEL\r\n".format(amount)
        # 見づらいので分解(遅くなるけど無視)
        disp_msg = tip_user +tip_src +tip_dst +tip_am
        await _disp_rep_msg( client, message,'送金(tip)','以下のように送金しました。',disp_msg )
        ################################
    return

# @breif ,rain (amount) とりあえずxselを1-10
# @return  user - seln address list
async def _cmd_rain(client, message):
    # ----------------------------
    # -- 暫定仕様 --
    # ------------------------
    # オフラインではない人で、XSELを均等にプレゼント。
    if message.content.startswith(",rain"):
        # 引数からdstaddressを取得する。
        # ユーザからsrcaddressを取得する。
        print("tip {0}:{1}".format(message.author, message.content))
        params       = message.content.split()
        user         = str(message.author)
        user_mention = message.author.mention
        src_addr = ""

        if (len(params) != 2):
            await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが間違えています。".format(user_mention))
            return
        if False == params[1].isdigit():
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, params[1]))
            return
        amount = 0
        try:
            amount  = int(params[1])
        except:
            # exceptionで戻る
            await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
            return

        # amount制限
        if (1 > amount):
            await client.send_message(message.channel, "{0}様、amountのパラメータが下限を超えています。amount:{1} < 1".format(user_mention, amount))
            return
        if (amount > RAIN_AMOUNT_MAX):
            await client.send_message(message.channel, "{0}様、amountのパラメータが上限を超えています。amount:{1} > {2}".format(user_mention, amount, RAIN_AMOUNT_MAX))
            return
        # ----------------------------
        # まず自分のアドレス
        with closing(sqlite3.connect(DBNAME)) as connection:
            cursor = connection.cursor()
            row = _get_user_row(cursor, user)
            if row is not None:
                # src アドレス取得
                src_addr = str(row[1])
            else:
                await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
                return
        # ----------------------------
        # オンラインリストから条件合致したものをフィルタ
        # onlineユーザを取得
        online_users = []
        members = client.get_all_members()
        for member in members:
            if (discord.Status.online == member.status) and (False == member.bot):
                online_users.append(str(member))
        # print(online_users)
        # ------------------------
        # online_usersからdbのリストを取得

        # まず自分のアドレス
        # ちょっと効率悪いけど気にしない
        dst_user_addrs=[]
        for dst_user in online_users:
            with closing(sqlite3.connect(DBNAME)) as connection:
                cursor = connection.cursor()
                row = _get_user_row(cursor, dst_user)
                if row is not None:
                    # 取得したタプルペアをそのままリストに突っ込む
                    dst_user_addrs.append(row)

        # 確定したリストに対して送信
        sent_count = 0
        for row in dst_user_addrs:
            # これで
            dst_user = row[0]
            dst_addr = row[1]
            ################################
            # TODO ここでRPCにて残高確認する
            ################################

            ################################
            # TODO ここでRPCにて送金依頼
            ################################
            # if (user != dst_user)
            # src_addr,dst_addr,amount
            print(row[0], row[1])
            sent_count += 1
            # await client.send_message(message.channel, "{0}様、{1}, {2}, {3}で送金致しました。".format(user,src_addr,dst_addr,amount))

        ################################
        ra_user = "**所有者**\r\n{0} 様  \r\n".format(user)
        ra_src  = "**送信元**\r\n{0}     \r\n".format(src_addr)
        ra_sent = "**送信数**\r\n{0}     \r\n".format(sent_count)
        ra_am   = "**送金額**\r\n{0} XSEL\r\n".format(amount)
        # 見づらいので分解(遅くなるけど無視)
        disp_msg = ra_user +ra_src +ra_sent +ra_am
        await _disp_rep_msg( client, message,'送金(tip)','以下のように送金しました。',disp_msg )
        ################################

    return


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

##########################################
# debug
##########################################
# ユーザ確認
async def _cmd_dbg_info(client, message):
    if message.content.startswith(",dbg"):

        # send_ch = message.channel
        send_ch = message.author

        print("dbg {0}:{1}".format(send_ch, message.content))
        params = message.content.split()
        src_addr = ""
        if (len(params) < 3):
            await client.send_message(send_ch, "dbgコマンドが間違えている.")
            return

        # ,dbg members online
        # ,dbg members all
        if "members" == str(params[1]):
            if "online" == str(params[2]):
                members = client.get_all_members()
                # onlineユーザ取得
                online_users = list(filter(lambda x: (x.bot == False) and (x.status == discord.Status.online), members))
                # Member obj->mapでmember名->list->str->send
                await client.send_message(send_ch, str(list(map(str,online_users))))
            elif "all" == str(params[2]):
                members = client.get_all_members()
                # allユーザ(botのみ除く)
                all_users = list(filter(lambda x: x.bot == False, members))
                # Member obj->mapでmember名->list->str->send
                await client.send_message(send_ch, str(list(map(str,all_users))))

##########################################
# 表示
##########################################
# コマンドに対する応答
async def _disp_rep_msg( client, message, disp_name, disp_title, disp_msg ):
    # # 埋め込みメッセージ
    msg = discord.Embed(title=disp_title, type="rich",description=disp_msg, colour=0x3498db)
    # TODO iconが挿入されないので後で確認
    msg.set_author(name=disp_name, icon_url=client.user.avatar_url)
    txt_msg = await client.send_message(message.channel, embed=msg)
    # await client.add_reaction(txt_msg,'👍')


##########################################
# RPC
##########################################
# RPCでアドレスを作成する依頼を出す。
def _get_regist_address(user):
    # TODO ここでRPC経由でアドレスを取得する。

    # rpc_connection = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"%(myserver.rpc_user, myserver.rpc_password))
    # best_block_hash = rpc_connection.getbestblockhash()
    # print(rpc_connection.getblock(best_block_hash))

    return "Sxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"



