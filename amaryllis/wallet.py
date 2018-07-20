import discord
import sqlite3
import myserver
# import myserver_test as myserver
from contextlib import closing
from enum import Enum
# from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

#########################################################
# ,register
# discord ウォレットを作成する。
#
# ,address
# ウォレットアドレスを確認する。
#
# ,balance
# ウォレットの残高を確認する。
#
# ,tip (to) (amount)
# 「to」に対して、「amount」XSELを渡します。
# toには、discordの名前を指定してください。
# 例：,tip seln#xxxx 3
#
# ,rain (amount)
# オフラインではない人で、挿入金額が5XSEL未満の人にXSELを均等にプレゼント。
# 対象はdiscord walletです。
#
# -------------------------------------------------------
# [次期対応]
# ,info
# 現在のXSELの価格を表示します。
#
# ,deposit
# ウォレットからdiscord walletに送金します。
# ウォレットにXSELを入れるには、このアドレスに送金してください。
#
# ,withdraw (addr)(amount)
# 「addr」に対して、「amount」XSELを送金します。
#########################################################

cmd_admin_str="ironwood#7205"
# amount上限
WITHDRAW_AMOUNT_MAX = 1000.0
TIP_AMOUNT_MAX      = 1000.0
RAIN_AMOUNT_MAX     = 10.0
RAIN_AMOUNT_MIN     = 1.0
RAIN_AMOUNT_TARGET_TH = 5.0

# 登録データ
DBNAME = 'discordwallet.db'
REG_TABLENAME= 'wallet'
MAX_RECORD = 10000000

# ダミーのアドレス(本当のアドレスはSから. tは仮となる)
INIT_ADDR_DUMMY='tXXXXXXXXXXXXXXXXXXXXXXXXXX'

# command string
_CMD_STR_REGISTER      = ",register"
_CMD_STR_ADDRESS       = ",address"
_CMD_STR_BALANCE       = ",balance"
_CMD_STR_TIP           = ",tip"
_CMD_STR_RAIN          = ",rain"
_CMD_STR_INFO          = ",info"
_CMD_STR_DEPOSIT       = ",deposit"
_CMD_STR_WITHDRAW      = ",withdraw"

# dbg
_CMD_STR_DUMP          = ",dump"
_CMD_STR_DBG_CMD       = ",dbg"
_CMD_STR_TEST_REGISTER = ",testregister"
# adminsend, adminself
_CMD_STR_ADMIN_SEND    = ",adminsend"
_CMD_STR_ADMIN_SELF    = ",adminself"
_CMD_STR_ADMIN_BALANCE = ",adminbalance"

class WalletInfo():
    def __init__(self, userid='', user_name='', address='', balance=0.0, pending=0.0):
        self.userid    = userid
        self.user_name = user_name
        self.address   = address
        self.balance   = balance
        self.pending   = pending
    
    #TODO 後で計算処理を追加

# db table 要素の番号
class WalletNum(Enum):
    ID      = 0
    USER    = 1
    ADDR    = 2
    BALANCE = 3
    PENDING = 4

def on_ready():
    _create_table()

async def on_message_inner(client, message):
    # dump
    if message.channel.id == myserver.CH_ID_REGISTER:
        # 登録
        await _cmd_register(client, message)
    elif message.channel.id == myserver.CH_ID_WALLET:
        # WALLET
        await _cmd_address(client, message)
        await _cmd_balance(client, message)
        await _cmd_tip(client, message)
        await _cmd_rain(client, message)
        # 未実装
        await _cmd_info(client, message)
        await _cmd_withdraw(client, message)
        await _cmd_deposit(client, message)
    elif message.channel.id == myserver.CH_ID_ADMIN:
        # ADMIN
        await _cmd_dump(client, message)
        await _cmd_dbg_cmd(client, message)
        await _cmd_test_register(client, message)
        await _cmd_admin_send(client, message)
        await _cmd_admin_self(client, message)
        await _cmd_admin_balance(client, message)

    return

# ----------------------------------------
# コマンド
# ----------------------------------------

# @breif ,register ウォレットを作成します。:ユーザ登録するだけ
# @return seln address
async def _cmd_register(client, message):
    if not message.content.startswith(_CMD_STR_REGISTER):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_REGISTER, message.author, message.content))
    # param get
    params       = message.content.split()
    userid       = str(message.author.id)
    user_name    = str(message.author)
    user_mention = message.author.mention

    if (len(params) >= 2):
        await client.send_message(message.channel, "{0}様、申し訳ございません。いらない引数があります。".format(user_mention))
        return

    accept = False

    # ユーザ登録を行う前にユーザがいるかどうか確認する.
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        count = count_record(cursor)
        # ユーザが登録済みかを確認する.
        row = _get_user_row(cursor, userid)
        if row is not None:
            # ユーザ名チェック
            check_user = row[WalletNum.USER.value]
            if check_user != user_name:
                # ユーザが存在するが現在と名称が異なる場合、ユーザ名を更新する。
                if not _update_username(cursor, userid, user_name):
                    await client.send_message(message.channel, "{0}様、もう登録されておりますよ。".format(user_mention))
                    return
                else:
                    connection.commit()
            await client.send_message(message.channel, "{0}様、もう登録されておりますよ。".format(user_mention))
            return
        else:
            pass # ユーザが登録されていない.

        if count[0] > MAX_RECORD:
            await client.send_message(message.channel, "{0}様、もう業務時間終了致しました。".format(user_mention))
            return
    #################################
    # 初期情報
    # 送信用にアドレス入れておく
    address = INIT_ADDR_DUMMY
    balance = 1000.0
    pending = 0.0
    #################################
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        count = count_record(cursor)
        # コミット/アドレス上書き(registerにおいては上書きはない)
        update = _insert_user(cursor, userid, user_name, address, balance, pending)
        connection.commit()
        if _is_exists_record(cursor, userid, user_name, address, balance, pending):
            if not update:
                await client.send_message(message.channel, "{0}様、お受付いたしました".format(user_mention))
            else:
                await client.send_message(message.channel, "{0}様、前のアドレスを喪失してしまいました。".format(user_mention))
            # OK
            accept = True
        else:
            # NG
            await client.send_message(message.channel, "{0}さま、なんか失敗しました。".format(user_mention))
    if accept:
        ################################
        rg_user  = "**所有者**\r\n{0} 様({1}) \r\n".format(user_name, userid)
        rg_src   = "**アドレス**\r\n{0}   \r\n".format(address)
        disp_msg = rg_user +rg_src
        await _disp_rep_msg( client, message,'登録情報','',disp_msg )
        ################################
    return

# @breif ,dump デバッグコマンド。
# @return  user - seln address list
async def _cmd_dump(client, message):
    if not message.content.startswith(_CMD_STR_DUMP):
        # なにもしない
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_DUMP, message.author, message.content))
    user = str(message.author)
    # 特殊なユーザでない場合、反応しない
    if (user != cmd_admin_str):
        return
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        _dump_all(cursor)
        # await _dump_all_private(client, message, cursor)


# @breif ,address  : wallet Value
# @return xsel Value
async def _cmd_info(client, message):
    if not message.content.startswith(_CMD_STR_INFO):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_INFO, message.author, message.content))
    ################################
    # TODO 現在のXSELの価格を表示します。selndに問い合わせ
    ################################
    value = "0.0000000"
    ################################
    ad_user = "**価格**\r\n{0}   \r\n".format(value)
    disp_msg = ad_user
    await _disp_rep_msg( client, message,'XSELの価格','',disp_msg )
    ################################
    return

# @breif ,address command : wallet address
# @return  seln address
async def _cmd_address(client, message):
    if not message.content.startswith(_CMD_STR_ADDRESS):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADDRESS, message.author, message.content))
    params       = message.content.split()
    username     = str(message.author)
    userid       = str(message.author.id)
    user_mention = message.author.mention

    if (len(params) >= 2):
        await client.send_message(message.channel, "{0}様、申し訳ございません。いらない引数があります。".format(user_mention))
        return
    # userid でDBからaddr取得
    src_addr = ''
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, userid)
        # print(row)
        if row is not None:
            src_addr = row[WalletNum.ADDR.value]
        else:
            await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
            return

    ################################
    ad_user = "**所有者**\r\n{0} 様 ({1})  \r\n".format(username, userid)
    ad_src  = "**アドレス**\r\n{0}     \r\n".format(src_addr)
    disp_msg = ad_user +ad_src
    await _disp_rep_msg( client, message,'登録情報','',disp_msg )
    ################################
    return


# @breif ,balance : wallet balance
# @return wallet balance
async def _cmd_balance(client, message):
    # ウォレットの残高を確認します。
    if not message.content.startswith(_CMD_STR_BALANCE):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_BALANCE, message.author, message.content))
    # userからaddressを取得する。
    params       = message.content.split()
    userid       = str(message.author.id)
    username     = str(message.author)
    user_mention = message.author.mention

    src_addr = ""
    if (len(params) > 1):
        await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが余計です。".format(user_mention))
        return

    src_balance = 0.0
    src_pending = 0.0
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, userid)
        if row is not None:
            # src アドレス取得
            src_addr    = row[WalletNum.ADDR.value]
            src_balance = row[WalletNum.BALANCE.value]
            src_pending = row[WalletNum.PENDING.value]
        else:
            await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
            return

    ################################
    # 残高表示
    ################################
    bl_user     = "**所有者**\r\n{0} 様 ({1}) \r\n".format(username, userid)
    bl_balance  = "**残高**\r\n{0} XSEL   \r\n".format(src_balance)
    bl_pending  = "**PENDING**\r\n{0} XSEL\r\n".format(src_pending)
    disp_msg = bl_user +bl_balance + bl_pending
    await _disp_rep_msg( client, message,'残高(BALANCE)','残高でございます。',disp_msg )
    ################################
    return

# @breif ,tip (to) (amount)
async def _cmd_tip(client, message):
    if not message.content.startswith(_CMD_STR_TIP):
        return
    # 「to」に対して、「amount」XSELを渡します。 toには、discordの名前を指定してください。
    # 例：,tip seln#xxxx 3
    dbg_print("{0} {1}:{2}".format(_CMD_STR_TIP, message.author, message.content))
    # 引数からdstaddressを取得する。
    # ユーザからsrcaddressを取得する。
    params       = message.content.split()
    username     = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = message.author.mention

    to_user = ""
    src_addr = ""
    dst_addr = ""
    if (len(params) != 3):
        await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが間違えています。".format(user_mention))
        return
    amount = 0.0
    try:
        to_user = params[1]
        amount  = float(params[2])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
        return

    # amount制限
    if amount > TIP_AMOUNT_MAX:
        await client.send_message(message.channel, "{0}様、amountのパラメータが上限を超えています。amount:{1} XSEL > {2} XSEL".format(user_mention, amount, TIP_AMOUNT_MAX))
        return
    # ----------------------------
    # 相手のアドレス探しておく
    to_userid=''
    member = _get_user2member(client, to_user)  # メンバ取得
    if member is not None:
        if False == member.bot:
            to_userid = member.id
    # なかったら抜ける。
    if to_userid == '':
        await client.send_message(message.channel, "{0}様、{1}という方は、おりません。".format(user_mention, to_user))
        # 対象ユーザがいないので終了
        return
    # ----------------------------
    # DBから自分のアドレス探してbalance
    src_balance = 0.0
    dst_balance = 0.0
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, src_userid)
        if row is not None:
            src_balance = row[WalletNum.BALANCE.value]
        else:
            await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
            return
        if src_balance < amount: # 残高がamountより下だったらエラー
            await client.send_message(message.channel, "{0}様、残高が足りません。balance:{1} XSEL / amount:{2} XSEL".format(user_mention, src_balance, float(amount)))
            return

        # 残高からamount分引いて更新
        src_balance = src_balance - amount
        if not _update_balance(cursor, src_userid, src_balance):
            await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
            return

        # TODO ユーザを探す
        row = _get_user_row(cursor, to_userid)
        if row is not None:
            # 発見
            dst_balance = row[WalletNum.BALANCE.value]
        else:
            await client.send_message(message.channel, "{0}様、TO:{1}様のアドレスは登録されていないようです。".format(user_mention, to_user))
            return
        # balanceに加算
        dst_balance = dst_balance + amount
        if not _update_balance(cursor, to_userid, dst_balance):
            await client.send_message(message.channel, "{0}様、{1}様の残高が更新できませんでした。".format(user_mention, to_user))
            return
        connection.commit()
    ################################
    tip_user = "**送信者**\r\n{0} 様 ({1})  \r\n".format(username, src_userid)
    tip_dst  = "**送信先**\r\n{0} 様 ({1})    \r\n".format(to_user, to_userid)
    tip_am   = "**送金額**\r\n{0} XSEL\r\n".format(amount)
    tip_am   = "**残高**\r\n{0} XSEL\r\n".format(src_balance)
    disp_msg = tip_user +tip_dst +tip_am
    await _disp_rep_msg( client, message,'送金(tip)','以下のように送金いたしました。',disp_msg )
    ################################
    return

# @breif ,rain (amount) : amountを対象に分配
# @return  user - seln address list
async def _cmd_rain(client, message):
    if not message.content.startswith(_CMD_STR_RAIN):
        return
    # ----------------------------
    # -- 暫定仕様 --
    # ------------------------
    # オフラインではない人で、XSELを均等にプレゼント。
    dbg_print("{0} {1}:{2}".format(_CMD_STR_RAIN, message.author, message.content))
    # 引数からdstaddressを取得する。
    # ユーザからsrcaddressを取得する。
    params       = message.content.split()
    user         = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = message.author.mention

    if (len(params) != 2):
        await client.send_message(message.channel, "{0}様、申し訳ございません。パラメータが間違えています。".format(user_mention))
        return
    amount = 0.0
    try:
        amount  = float(params[1])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
        return
    # amount制限
    if (amount < RAIN_AMOUNT_MIN):
        await client.send_message(message.channel, "{0}様、amountのパラメータが下限を超えています。amount:{1} XSEL < {2} XSEL".format(user_mention, amount, RAIN_AMOUNT_MIN))
        return
    if (amount > RAIN_AMOUNT_MAX):
        await client.send_message(message.channel, "{0}様、amountのパラメータが上限を超えています。amount:{1} XSEL > {2} XSEL".format(user_mention, amount, RAIN_AMOUNT_MAX))
        return
    # ----------------------------
    # まず自分のアドレス
    src_balance = 0.0
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row    = _get_user_row(cursor, src_userid)
        if row is not None:
            src_balance = row[WalletNum.BALANCE.value]
        else:
            await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
            return

    if src_balance < amount: # 残高がamountより下だったらエラー
        await client.send_message(message.channel, "{0}様、残高が足りません。balance:{1} XSEL / amount:{2} XSEL".format(user_mention, src_balance, float(amount)))
        return
    # ----------------------------
    # onlineユーザを取得
    # ----------------------------
    online_usersid = []
    members = client.get_all_members()
    for member in members:
        # オンライン & botではない & 自分ではない でフィルタ
        if (discord.Status.online == member.status) and (False == member.bot) and (src_userid != str(member.id)):
            online_usersid.append(str(member.id))
    # print(online_usersid)
    
    if len(online_usersid) <= 0:
        await client.send_message(message.channel, "{0}様、オンラインの方がいません。".format(user_mention))
        return
    # ------------------------
    # checkRainAmount
    # ------------------------
    # online_usersidからdbのリストを取得
    dst_user_addrs=[]
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        for dst_userid in online_usersid:
            row = _get_user_row(cursor, dst_userid)
            if row is not None:
                bl = row[WalletNum.BALANCE.value]
                # RAIN_AMOUNT_TARGET_THより下のXSELである場合は、RAIN対象とする。
                if bl < RAIN_AMOUNT_TARGET_TH:
                    dst_user_addrs.append(dst_userid)

    # 対象ユーザが０であるか？
    send_user_count = len(dst_user_addrs)
    if send_user_count <= 0:
        await client.send_message(message.channel, "{0}様、対象の方がいません。".format(user_mention))
        return

    # ------------------------
    # RainAmount計算
    # ------------------------
    rain_amount = amount * float(send_user_count)
    # 1 XSEL以下だったら捨てる
    if rain_amount > src_balance:
        await client.send_message(message.channel, "{0}様、残高が足りません。オンラインユーザ数:{1}, amount:{2} XSEL".format(user_mention, send_user_count, amount))
        return
    # ------------------------
    # 確定したリストに対して送信
    # ------------------------
    total_sent = 0.0
    sent_count = 0
    # 一個でも失敗したら更新しない。
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        # ---------------------------------------
        # 残高からRainAmount分引いて更新
        src_balance = src_balance - rain_amount
        if not _update_balance(cursor, src_userid, src_balance):
            await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
            return
        # まだ閉じない
        # ---------------------------------------
        for dst_userid in online_usersid:
            dst_balance = 0.0
            dst_username = ''
            row = _get_user_row(cursor, dst_userid)
            if row is not None:
                dst_balance = row[WalletNum.BALANCE.value]
                dst_username = row[WalletNum.USER.value]
            else:
                # 確実に存在するはずなのでここに来たらDBが壊れている。
                await client.send_message(message.channel, "{0}様、{1}という方は登録されていないようです。".format(user_mention, dst_username))
                return
            # 量以上に配布していないかをチェック
            if total_sent >= rain_amount:
                await client.send_message(message.channel, "{0}様、見込みより多く送金しているため取りやめました。sent:{1} / send:{2}".format(user_mention, total_sent, rain_amount))
                return
            # ---------------------------------------
            # balanceに加算
            total_sent += amount
            dst_balance = dst_balance + amount
            if not _update_balance(cursor, dst_userid, dst_balance):
                await client.send_message(message.channel, "{0}様、{1}様の残高が更新できませんでした。".format(user_mention, dst_username))
                return
            sent_count += 1
        connection.commit()

    ################################
    ra_user  = "**所有者**\r\n{0} 様  \r\n".format(user, src_userid)
    ra_sent  = "**送信数**\r\n{0}     \r\n".format(sent_count)
    ra_total = "**総送金額**\r\n{0} XSEL\r\n".format(total_sent)
    ra_am    = "**一人あたりの送金料**\r\n{0} XSEL\r\n".format(amount)
    disp_msg = ra_user +ra_sent +ra_total +ra_am
    await _disp_rep_msg( client, message,'送金(rain)','以下のように送金しました。',disp_msg )
    ################################
    return

####################################################################################
# 未対応、未実装        withdraw, info, deposit
####################################################################################

# @breif ,withdraw (addr) (amount) : withdraw
# @return  user - seln address list
async def _cmd_withdraw(client, message):
    # 「addr」に対して、「amount」XSELを送金します。
    if not message.content.startswith(_CMD_STR_WITHDRAW):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_WITHDRAW, message.author, message.content))

    ####################################################################################
    # TODO 未実装メッセージ
    disp_msg=""
    await _disp_rep_msg( client, message,'','すみません。未対応です。m(_ _)m',disp_msg )
    return
    ####################################################################################

    # 引数からdstaddressを取得する。
    # ユーザからsrcaddressを取得する。
    params = message.content.split()
    userid = str(message.author.id)
    username = str(message.author)
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
        amount   = float(params[2])
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
        row = _get_user_row(cursor, userid)
        if row is not None:
            # src アドレス取得
            src_addr = row[WalletNum.ADDR.value]
        else:
            await client.send_message(message.channel, "{0}様、アドレスの登録がお済みでないようです。".format(user_mention))
            return

    ################################
    # TODO ここでRPCにて送金依頼
    ################################
    # src_addr,dst_addr,amount

    ################################
    wd_user = "**所有者**\r\n{0} 様({1})  \r\n".format(username, userid)
    wd_src  = "**送信元**\r\n{0}     \r\n".format(src_addr)
    wd_dst  = "**送信先**\r\n{0}     \r\n".format(dst_addr)
    wd_am   = "**送金額**\r\n{0} XSEL\r\n".format(amount)
    disp_msg = wd_user +wd_src +wd_dst +wd_am
    await _disp_rep_msg( client, message,'送金(withdraw)','以下のように送金しました。',disp_msg )
    ################################
    return


async def _cmd_deposit(client, message):
    if not message.content.startswith(_CMD_STR_DEPOSIT):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_DEPOSIT, message.author, message.content))
    disp_msg=""
    await _disp_rep_msg( client, message,'','すみません。未対応です。m(_ _)m',disp_msg )
    return

##########################################
# Utility
##########################################

def _create_table():
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()

        # executeメソッドでSQL文を実行する
        # id '449934944785924096'
        # username ironwood@7205のようなユーザ名 : 備考みたいなもの
        # address : selnアドレス : しばらくはdummyアドレス
        # balance : 残高
        # pending : 仮
        create_table = 'create table if not exists ' \
            + REG_TABLENAME + ' (id varchar(32), username varchar(64), address varchar(64), balance real, pending real)'
        print(create_table)
        cursor.execute(create_table)
        connection.commit()

# insert_user
def _insert_user(cursor, userid, username, address, balance, pending):
    update = False
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set username=? set address=? set balance=? set pending=? where id=?'
        print(sql)
        cursor.execute(sql, (username, address, balance, pending, userid))
        update = True
    else:
        sql = 'insert into ' + REG_TABLENAME + ' (id, username, address, balance, pending) values (?,?,?,?,?)'
        print(sql)
        cursor.execute(sql, (userid, username, address, balance, pending))
    return update

# 残高更新
def _update_balance(cursor, userid, balance):
    update = False
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set balance=? where id=?'
        print(sql)
        cursor.execute(sql, (balance, userid))
        update = True
    return update

# username更新
def _update_username(cursor, userid, username):
    update = False
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set username=? where id=?'
        print(sql)
        cursor.execute(sql, (username, userid))
        update = True
    return update

# exist userid True:exist / False:
def _get_user_row(cursor, userid):
    select_sql = 'select * from ' + REG_TABLENAME + ' where id=?'
    print(select_sql)
    cursor.execute(select_sql, (userid,))
    # 見つかったものを返却
    return cursor.fetchone()

# exist user True:exist / False:
def _is_exists_userid(cursor, userid):
    select_sql = 'select * from ' + REG_TABLENAME + ' where id=?'
    print(select_sql)
    cursor.execute(select_sql, (userid,))
    if cursor.fetchone() is None:
        return False
    else:
        return True

# exist user & address pare
def _is_exists_record(cursor, userid, user_name, address, balance, pending):
    select_sql = 'select * from ' + REG_TABLENAME + ' where id=? and user_name=? and address=? and balance=? and pending=?'
    # select_sql = 'select * from ' + REG_TABLENAME + ' where id=?'
    print(select_sql)
    cursor.execute(select_sql, (userid, user_name, address, balance, pending))
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

# ユーザ名からmember Objを返す.
def _get_user2member(client, username):
    found_member = None
    members = client.get_all_members()  # メンバ取得
    for member in members:
        if username == str(member):
            found_member = member
            break
    return found_member

# オンラインメンバーを抜き出す.
def _get_online_members(client, message):
    online_members = []
    # onlineユーザ取得
    if len(members) > 0:
        online_members = list(filter(lambda x: (x.bot == False) and (x.status == discord.Status.online) and (message.author.id != member.id), client.get_all_members()))
    return online_members

##########################################
# debug
##########################################
# ユーザ確認
async def _cmd_dbg_cmd(client, message):
    if message.content.startswith(_CMD_STR_DBG_CMD):
        dbg_print("{0} {1}:{2}".format(_CMD_STR_DBG_CMD, message.author, message.content))

        # send_ch = message.channel
        send_ch = message.author
        # user         = str(message.author)

        params = message.content.split()
        src_addr = ""
        if (len(params) < 3):
            await client.send_message(send_ch, "dbgコマンドが間違えている.")
            return

        # ,dbg members online
        # ,dbg members all
        if "members" == str(params[1]):
            if "online" == str(params[2]):
                # members = client.get_all_members()
                # # onlineユーザ取得
                online_users = list(filter(lambda x: (x.bot == False) and (x.status == discord.Status.online), members))
                # # Member obj->mapでmember名->list->str->send
                await client.send_message(send_ch, str(list(map(str,online_users))))
            elif "all" == str(params[2]):
                members = client.get_all_members()
                # allユーザ(botのみ除く)
                all_users = list(filter(lambda x: x.bot == False, members))
                users_dict={}

                # ユーザとユーザIDの辞書を作成
                for member in all_users:
                    users_dict[str(member)] = member.id

                # ユーザIDからユーザを取得
                for value in users_dict.values():
                    # print(str(value))
                    obj = await client.get_user_info(value)
                    print(str(obj))

                await client.send_message(send_ch, str(users_dict))
    return

##########################################
# admin用
# cmd_admin_strに設定されているユーザしか実行できない。
##########################################
async def _cmd_test_register(client, message):
    if not message.content.startswith(_CMD_STR_TEST_REGISTER):
        return
    # 送信用にアドレス入れておく
    testuserid = '999999999999999999'
    testuser   = 'seni#6719'
    address    = INIT_ADDR_DUMMY
    balance    = 1000.0
    pending    = 0.0

    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        count = count_record(cursor)
        # ユーザが登録済みかを確認する.
        if _is_exists_userid(cursor, testuserid): # すでにユーザが存在する
            await client.send_message(message.channel, "{0}様はもう登録されておりますよ。".format(testuser))
            return
        update = _insert_user(cursor, testuserid ,testuser ,address ,balance ,pending)
        connection.commit()
    return

# balanceに値を設定する
#ex) ,adminsend ironwood#7205 1000.0
async def _cmd_admin_send(client, message):
    if not message.content.startswith(_CMD_STR_ADMIN_SEND):
        return
    src_user     = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)
    params       = message.content.split()

    if (src_user != cmd_admin_str):
        return

    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADMIN_SEND, message.author, message.content))

    if (len(params) != 3):
        await client.send_message(message.channel, "コマンドが間違えています.")
        return

    user_info = _get_user2member(client, params[1])
    if user_info is None:
        await client.send_message(message.channel, "コマンドが間違えています.2")
        return
    dst_userid = user_info.id
    try:
        amount  = float(params[2])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
        return

    dst_balance = 0.0
    dst_pending = 0.0
    dst_username = ''
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, dst_userid)
        if row is not None:
            dst_balance  = row[WalletNum.BALANCE.value]
            dst_pending  = row[WalletNum.PENDING.value]
            dst_username = row[WalletNum.USER.value]

            dst_balance += amount
            if not _update_balance(cursor, dst_userid, dst_balance):
                await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
                return
        else:
            await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
            return
        connection.commit()

    ################################
    # ADMIN 残高表示
    ################################
    bl_user     = "**所有者**\r\n{0} 様 ({1}) \r\n".format(dst_username, dst_userid)
    bl_balance  = "**残高**\r\n{0} XSEL   \r\n".format(dst_balance)
    bl_pending  = "**PENDING**\r\n{0} XSEL\r\n".format(dst_pending)
    disp_msg = bl_user +bl_balance + bl_pending
    await _disp_rep_msg( client, message,'残高(BALANCE)','残高更新しました。',disp_msg )
    ################################
    return

# 自分のbalanceに値を設定する
# ,adminself 1000,0
async def _cmd_admin_self(client, message):
    if not message.content.startswith(_CMD_STR_ADMIN_SELF):
        return
    src_username = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)
    params       = message.content.split()

    if (src_username != cmd_admin_str):
        return

    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADMIN_SELF, message.author, message.content))

    if (len(params) != 2):
        await client.send_message(message.channel, "コマンドが間違えています.")
        return
    try:
        amount  = float(params[1])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, amount))
        return

    src_balance = 0.0
    src_pending = 0.0
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row    = _get_user_row(cursor, dst_userid)
        if row is not None:
            src_balance = row[WalletNum.BALANCE.value]
            src_pending = row[WalletNum.PENDING.value]
            src_balance += amount
            if not _update_balance(cursor, src_userid, src_balance):
                await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
                return
        else:
            await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
            return
        connection.commit()

    ################################
    # ADMIN 残高表示
    ################################
    bl_user     = "**所有者**\r\n{0} 様 ({1}) \r\n".format(src_username, src_userid)
    bl_balance  = "**残高**\r\n{0} XSEL   \r\n".format(src_balance)
    bl_pending  = "**PENDING**\r\n{0} XSEL\r\n".format(src_pending)
    disp_msg = bl_user +bl_balance + bl_pending
    await _disp_rep_msg( client, message,'残高(BALANCE)','残高更新しました。',disp_msg )
    ################################
    return

# discord balance total xsel
# ,adminbalance
# discord上の総額を表示
async def _cmd_admin_balance(client, message):
    if not message.content.startswith(_CMD_STR_ADMIN_BALANCE):
        return
    src_user     = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)
    params       = message.content.split()

    if (src_user != cmd_admin_str):
        return

    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADMIN_SEND, message.author, message.content))

    if (len(params) != 1):
        await client.send_message(message.channel, "コマンドが間違えています.")
        return

    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        # ---------------------------------------
        total_balane = 0.0
        select_sql = 'select * from ' + REG_TABLENAME
        cursor.execute(select_sql)
        while 1:
            dst_balance = 0.0
            dst_username = ''
            row = cursor.fetchone();
            if row is not None:
                dst_balance = row[WalletNum.BALANCE.value]
                dst_username = row[WalletNum.USER.value]
            else:
                break
            total_balane += dst_balance
    ################################
    totalb_src  = "**総額**\r\n{0} XSEL\r\n".format(total_balane)
    disp_msg = totalb_src
    await _disp_rep_msg( client, message,'discord wallet','結果を表示します。',disp_msg )
    ################################
    return
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

# コンソールメッセージ
def dbg_print( msg_str ):
    print(msg_str)
    pass

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


