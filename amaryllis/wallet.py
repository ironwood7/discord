import discord
import sqlite3
import myserver
# import myserver_test as myserver
from contextlib import closing
from enum import Enum
# from decimal import Decimal, getcontext, ROUND_DOWN, FloatOperation
from decimal import Decimal, getcontext, ROUND_DOWN, FloatOperation
from datetime import datetime
import logging.config
import bitcoin
from bitcoin.rpc import Proxy

# getcontext.precは、デフォルト28のまま

# from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

#########################################################
# ,register
# discord ウォレットを作成する。
#
# ,deposit
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
# オフラインではない人で、XSELを均等にプレゼント。
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
# -------------------------------------------------------
#【要望対応】
#・エラーメッセージをすべてメンション付きにしたい
#・コマンド名は完全一致以外は無視
#・BalanceのPendingメッセージの削除
#・送金時の (391247317140897804)の削除
#・残高表示は小数８桁まで
#【その他対応】
#・チャンネルをadmin / walletのみに変更
#・内部計算すべてDecimalに変更
#・rainの上限撤廃
#・DBの数値REALをTEXTに変更（数値誤差回避のため）
#・小数点は一律可とする
#【課題】
#・rich replyにアイコン設定
#・rain対象をidle（退席中）に拡大するか。
#
#########################################################

cmd_admin_lst=["seni#6719", "ironwood#7205", "ysk-n#4046", "sunday#1914"]
# amount上限
WITHDRAW_AMOUNT_MIN   = "0.00000001"
TIP_AMOUNT_MIN        = "0.00000001"
RAIN_AMOUNT_MIN       = "1.00000000"
RAIN_ONE_AMOUNT_MIN   = "0.00000001"
RELEASE_VERSION       = "Version:0.7"

# 手数料
TRANSACTION_FEE = "0.001"

COIN = 100000000

# 登録データ
DBNAME        = 'discordwallet.db'
REG_TABLENAME = 'wallet'
MAX_RECORD    = 10000000


INIT_REG_BALANCE = "0"
# ダミーのアドレス(本当のアドレスはSから. tは仮)
# 後で本物のアドレスに入れ替える用
INIT_ADDR_DUMMY  = 'not create'

# command string
_CMD_STR_REGISTER      = ",register"
_CMD_STR_DEPOSIT       = ",deposit"
_CMD_STR_BALANCE       = ",balance"
_CMD_STR_TIP           = ",tip"
_CMD_STR_RAIN          = ",rain"
_CMD_STR_INFO          = ",info"
_CMD_STR_DEPOSIT       = ",deposit"
_CMD_STR_WITHDRAW      = ",withdraw"
_CMD_STR_VERSION       = ",version"
# adminsend, adminself
_CMD_STR_ADMIN_SEND    = ",adminsend"
_CMD_STR_ADMIN_SELF    = ",adminself"
_CMD_STR_ADMIN_BALANCE = ",adminbalance"
# dbg
_CMD_STR_DUMP          = ",dump"
_CMD_STR_DBG_CMD       = ",dbg"

COLUMN_AUTONUM = 'no'
COLUMN_ID = 'id'
COLUMN_USER = 'username'
COLUMN_ADDRESS = 'address'
COLUMN_BALANCE = 'balance'
COLUMN_PENDING = 'pending'
COLUMN_LASTUPDATE = 'lastupdate'

logger = logging.getLogger()

# db table 要素の番号
class WalletNum(Enum):
    ID      = 0
    USER    = 1
    ADDR    = 2
    BALANCE = 3
    PENDING = 4
    LASTUPDATE = 5

def on_ready():
    _create_table()
    logging.config.fileConfig('walletlogging.conf')
    bitcoin.SelectParams("mainnet")
    # Decimalの計算:float禁止
    getcontext().traps[FloatOperation] = True

async def on_message_inner(client, message):
    params = message.content.split()

    if (_CMD_STR_TIP == params[0]):
        await _cmd_tip(client, message, params)
    elif (_CMD_STR_RAIN == params[0]):
        await _cmd_rain(client, message, params)
    elif message.channel.id == myserver.CH_ID_WALLET:
        # 登録
        await _cmd_register(client, message, params)
        # WALLET
        await _cmd_balance(client, message, params)
        await _cmd_withdraw(client, message, params)
        #   未実装
        await _cmd_info(client, message, params)
        await _cmd_deposit(client, message, params)
    elif message.channel.id == myserver.CH_ID_ADMIN:
        # ADMIN
        await _cmd_dump(client, message, params)
        await _cmd_dbg_cmd(client, message, params)
        await _cmd_admin_send(client, message, params)
        await _cmd_admin_self(client, message, params)
        await _cmd_admin_balance(client, message, params)
        # other
        await _cmd_balance(client, message, params)
        await _cmd_version(client, message, params)
    return

# ----------------------------------------
# コマンド
# ----------------------------------------

# ,register
# discord ウォレットを作成する。
async def _cmd_register(client, message, params):
    if not params[0] == _CMD_STR_REGISTER:
        return
    userid       = str(message.author.id)
    user_name    = str(message.author)
    user_mention = message.author.mention

    logger.debug("register id={0} name={1}".format(userid, user_name))

    if (len(params) >= 2):
        await client.send_message(message.channel, "{0}！なにか間違っているわ！".format(user_mention))
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
                    await client.send_message(message.channel, "{0}！すでに登録ずみよ！".format(user_mention))
                    return
                else:
                    connection.commit()
            await client.send_message(message.channel, "{0}！すでに登録ずみよ！".format(user_mention))
            return
        else:
            pass # ユーザが登録されていない.

        if count[0] > MAX_RECORD:
            await client.send_message(message.channel, "{0}！すこし疲れたわね".format(user_mention))
            logger.warning("Over limit of user count.")
            return
    #################################
    # 初期情報
    # 送信用にアドレス入れておく
    address = INIT_ADDR_DUMMY
    balance = _round_down8(INIT_REG_BALANCE)
    pending = _round_down8("0.0")
    #################################
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        count = count_record(cursor)
        # コミット/アドレス上書き(registerにおいては上書きはない)
        update = _insert_user(cursor, userid, user_name, address, balance, pending)
        connection.commit()
        if _is_exists_record(cursor, userid, user_name, address, balance, pending):
            await client.send_message(message.channel, "{0}！できたわよ！".format(user_mention))
        else:
            # NG
            await client.send_message(message.channel, "{0}！失敗したわ！運営を訪ねなさい！".format(user_mention))
    return

# ,dump デバッグコマンド。printするだけ
async def _cmd_dump(client, message, params):
    if not params[0] == _CMD_STR_DUMP:
        # なにもしない
        return

    dbg_print("{0} {1}:{2}".format(_CMD_STR_DUMP, message.author, message.content))
    user = str(message.author)
    # 特殊なユーザでない場合、反応しない
    if not _is_admin_user(user):
        return
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        _dump_all(cursor)
        # await _dump_all_private(client, message, cursor)


# ,info
# 現在のXSELの価格を表示します。
async def _cmd_info(client, message, params):
    if not params[0] == _CMD_STR_INFO:
        return
    ####################################################################################
    # TODO 未実装メッセージ
    disp_msg=""
    await _disp_rep_msg( client, message,'','知らないわ！',disp_msg )
    return
    ####################################################################################
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

# ,deposit
# ウォレットアドレスを確認する。
async def _cmd_deposit(client, message, params):
    if not params[0] == _CMD_STR_DEPOSIT:
        return

    ####################################################################################
    # TODO 未実装メッセージ
    disp_msg=""
    await _disp_rep_msg( client, message,'','知らないわ！',disp_msg )
    return
    ####################################################################################

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
    ad_user = "**所有者**\r\n{0} 様\r\n".format(user_mention)
    ad_src  = "**アドレス**\r\n{0}\r\n".format(src_addr)
    disp_msg = ad_user +ad_src
    await _disp_rep_msg( client, message,'登録情報','',disp_msg )
    ################################
    return


# ,balance
# ウォレットの残高を確認する。
async def _cmd_balance(client, message, params):
    # ウォレットの残高を確認します。
    if not params[0] == _CMD_STR_BALANCE:
        return
    # userからaddressを取得する。
    userid       = str(message.author.id)
    username     = str(message.author)
    user_mention = message.author.mention

    src_addr = ""
    if (len(params) > 1):
        await client.send_message(message.channel, "{0}！間違っているわよ！".format(user_mention))
        return

    src_balance = _round_down8("0.0")
    src_pending = _round_down8("0.0")
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, userid)
        if row is not None:
            # src アドレス取得
            src_addr    = row[WalletNum.ADDR.value]
            src_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
            src_pending = _round_down8(str(row[WalletNum.PENDING.value]))
        else:
            await client.send_message(message.channel, "{0}！あなたなんて知らないわ！".format(user_mention))
            return

    ################################
    # 残高表示
    ################################
    bl_balance  = "**Balance**\r\n{0:.8f} XSEL\r\n".format(src_balance)
    # bl_pending  = "**PENDING**\r\n{0} XSEL\r\n".format(src_pending)
    # disp_msg = bl_user +bl_balance + bl_pending
    disp_msg = bl_balance
    await _disp_rep_msg( client, message, username, "" , disp_msg )
    ################################
    return

# ,tip (to) (amount)
# 「to」に対して、「amount」XSELを渡します。
# toには、discordの名前を指定してください。
# 例：,tip seln#xxxx 3
async def _cmd_tip(client, message, params):
    if not params[0] == _CMD_STR_TIP:
        return

    # 「to」に対して、「amount」XSELを渡します。 toには、discordの名前を指定してください。
    # 例：,tip seln#xxxx 3
    # 引数からdstaddressを取得する。
    # ユーザからsrcaddressを取得する。
    username     = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = message.author.mention

    to_user = ""
    src_addr = ""
    dst_addr = ""
    if (len(params) != 3):
        await client.send_message(message.channel, "{0}！間違っているわ！".format(user_mention))
        return
    amount = _round_down8("0.0")
    try:
        # print(params[1])
        to_user = params[1]
        amount  = _round_down8((params[2]))
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}！amount:{1}が間違ってるわ！".format(user_mention, params[2]))
        return

    # amount制限
    if amount < _round_down8(TIP_AMOUNT_MIN):
        await client.send_message(message.channel, "{0}！amount:{1}が間違ってるわ！".format(user_mention, params[2]))
        return
    # 相手のアドレス探しておく
    to_userid=''
    # member = _get_user2member(client, to_user)  # メンバ取得
    member = _get_usermention2member(client, to_user)  # メンバ取得
    if member is not None:
        if not member.bot:
            to_userid = member.id
    # なかったら抜ける。
    if to_userid == '':
        await client.send_message(message.channel, "{0}！{1}なんて知らないわ！".format(user_mention, to_user))
        # 対象ユーザがいないので終了
        return

    # 宛先が自分自身
    if to_userid == src_userid:
        await client.send_message(message.channel, "{0}！！怒るわよ！".format(user_mention))
        return
    # ----------------------------
    # DBから自分のアドレス探してbalance
    src_balance = _round_down8("0.0")
    dst_balance = _round_down8("0.0")
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, src_userid)
        if row is not None:
            src_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
        else:
            await client.send_message(message.channel, "{0}！あなたなんて知らないわ！".format(user_mention))
            return
        if src_balance < amount: # 残高がamountより下だったらエラー
            await client.send_message(message.channel, "{0}！XSELが足りないわよ！balance:{1:.8f} XSEL / amount:{2:.8f} XSEL".format(user_mention, src_balance, amount))
            return

        # 残高からamount分引いて更新
        
        src_after_balance = src_balance - amount
        if not _update_balance(cursor, src_userid, src_after_balance):
            await client.send_message(message.channel, "{0}！失敗したわね！！".format(user_mention))
            return

        logger.info("tip from id={0} name={1} before={2} send={3} after={4}".format(src_userid, username, src_balance, amount, src_after_balance))

        row = _get_user_row(cursor, to_userid)
        if row is not None:
            # 発見
            dst_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
        else:
            await client.send_message(message.channel, "{0}！{1}なんて知らないわ！".format(user_mention, to_user))
            return
        # balanceに加算
        dst_after_balance = dst_balance + amount
        if not _update_balance(cursor, to_userid, dst_after_balance):
            await client.send_message(message.channel, "{0}！失敗したわね！！".format(user_mention))
            return

        logger.info("tip to id={0} name={1} before={2} receive={3} after={4}".format(to_userid, member.nick, dst_balance, amount, dst_after_balance))

        connection.commit()
    ################################
    # tip_user = "**送金者**\r\n{0} 様\r\n".format(username)
    tip_dst  = "**to**\r\n{0}\r\n".format(member.mention)
    tip_am   = "**Amount**\r\n{0:.8f} XSEL\r\n".format(amount)
    disp_msg = tip_dst +tip_am
    await _disp_rep_msg( client, message, username, 'Tip', disp_msg )
    ################################
    return

# ,rain (amount)
# オフラインではない人で、XSELを均等にプレゼント。
async def _cmd_rain(client, message, params):
    if not params[0] == _CMD_STR_RAIN:
        return

    # 引数からdstaddressを取得する。
    # ユーザからsrcaddressを取得する。
    user         = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = message.author.mention

    if (len(params) != 2):
        await client.send_message(message.channel, "{0}！間違っているわよ！".format(user_mention))
        return
    amount = _round_down8("0.0")
    try:
        amount  = _round_down8(params[1])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}！送金額:{1}が間違っているわよ！".format(user_mention, params[1]))
        return
    # amount制限
    if amount < _round_down8(RAIN_AMOUNT_MIN):
        await client.send_message(message.channel, "{0}！rainは {1:.8f} XSEL以上にしなさい！".format(user_mention, _round_down8(RAIN_AMOUNT_MIN)))
        return
    # if amount > _round_down8(RAIN_AMOUNT_MAX):
    #     await client.send_message(message.channel, "{0}様、amountのパラメータが上限を超えています。amount:{1:.8f} XSEL > {2:.8f} XSEL".format(user_mention, amount, _round_down8(RAIN_AMOUNT_MAX)))
    #     return
    # ----------------------------
    # まず自分のアドレス
    src_balance = _round_down8("0.0")
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row    = _get_user_row(cursor, src_userid)
        if row is not None:
            src_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
        else:
            await client.send_message(message.channel, "{0}！あなたなんて知らないわ！".format(user_mention))
            return

    if src_balance < amount: # 残高がamountより下だったらエラー
        await client.send_message(message.channel, "{0}！XSELが足りないようね！balance:{1:.8f} XSEL / amount:{2:.8f} XSEL".format(user_mention, src_balance, amount))
        return
    # ----------------------------
    # onlineユーザを取得
    # ----------------------------
    online_usersid = []
    members = client.get_all_members()
    for member in members:
        # オンライン & botではない & 自分ではない でフィルタ
        # if (discord.Status.online == member.status ) and (False == member.bot) and (src_userid != str(member.id)):
        # オフライン、インビジブル以外はOKとする。
        if (discord.Status.offline != member.status and discord.Status.invisible != member.status ) and (False == member.bot) and (src_userid != str(member.id)):
            online_usersid.append(str(member.id))

    if len(online_usersid) <= 0:
        await client.send_message(message.channel, "{0}！誰もいないわね！".format(user_mention))
        return
    # ------------------------
    # checkRainAmount
    # ------------------------
    # online_usersidからdbのリストを取得
    receiver_user_ids=[]
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        for dst_userid in online_usersid:
            row = _get_user_row(cursor, dst_userid)
            if row is not None:
                receiver_user_ids.append(dst_userid)

    # 対象ユーザが０であるか？
    receiver_user_count = len(receiver_user_ids)
    if receiver_user_count <= 0:
        await client.send_message(message.channel, "{0}！誰もいないわね！".format(user_mention))
        return

    # ------------------------
    # RainAmount計算
    # ------------------------
    # 一人あたりの送金額
    send_amount = _round_down8(amount / receiver_user_count)
    # 0.00000001割ってたら送金しない
    if send_amount < _round_down8(RAIN_ONE_AMOUNT_MIN):
        await client.send_message(message.channel, "{0}！XSELが足りないわね！（オンラインユーザ数:{1}, 一人あたりの送金:{2:.8f} XSEL）".format(user_mention, send_user_count, send_amount))
        return
    total_amount = send_amount * receiver_user_count
    # ------------------------
    # 確定したリストに対して送信
    # ------------------------
    total_sent = _round_down8("0.0")
    sent_count = 0
    # 一個でも失敗したら更新しない。
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        # ---------------------------------------
        # 残高からRainAmount分引いて更新
        src_after_balance = src_balance - total_amount
        if not _update_balance(cursor, src_userid, src_after_balance):
            await client.send_message(message.channel, "{0}！失敗したわ！".format(user_mention))
            return
        # まだ閉じない
        # ---------------------------------------
        for dst_userid in receiver_user_ids:
            dst_balance = _round_down8("0.0")
            dst_username = ''
            row = _get_user_row(cursor, dst_userid)
            if row is not None:
                dst_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
                dst_username = row[WalletNum.USER.value]
            else:
                # 確実に存在するはずなのでここに来たらDBが壊れている。
                await client.send_message(message.channel, "{0}！なにかがおかしいわ！".format(user_mention))
                return
            # 量以上に配布していないかをチェック
            if total_sent >= total_amount:
                await client.send_message(message.channel, "{0}！バグってるわね！！（sent:{1:.8f} / send:{2:.8f}）".format(user_mention, total_sent, total_amount))
                return
            # ---------------------------------------
            # balanceに加算
            total_sent += send_amount
            dst_balance = dst_balance + send_amount
            if not _update_balance(cursor, dst_userid, dst_balance):
                await client.send_message(message.channel, "{0}！失敗したわね！！".format(user_mention))
                return
            sent_count += 1
        connection.commit()

    logger.info("rain from id={0} name={1} before={2} rain={3} after={4}".format(src_userid, user, src_balance, amount, src_after_balance))

    ################################
    ra_sent  = "**Receiver count**\r\n{0}\r\n".format(sent_count)
    ra_total = "**Rain Amount**\r\n{0:.8f} XSEL\r\n".format(total_sent)
    ra_am    = "**Amount / Receiver**\r\n{0:.8f} XSEL\r\n".format(send_amount)
    disp_msg = ra_sent +ra_total +ra_am
    await _disp_rep_msg( client, message, user, 'Rain', disp_msg )
    ################################
    return

async def _cmd_withdraw(client, message, params):
    # 「addr」に対して、「amount」XSELを送金します。
    if not params[0] == _CMD_STR_WITHDRAW:
        return
    # Decimalの計算:float禁止
    getcontext().traps[FloatOperation] = True

    # 引数からdstaddressを取得する。
    # ユーザからsrcaddressを取得する。
    userid = str(message.author.id)
    username = str(message.author)
    user_mention = message.author.mention
    dst_addr = ""
    src_addr = ""
    if (len(params) != 3):
        await client.send_message(message.channel, "{0}！書き方がおかしいわね！".format(user_mention))
        return

    amount   = 0
    dst_addr = params[1]

    if (not dst_addr.startswith("S")):
        await client.send_message(message.channel, "{0}！アドレスがおかしいわね！！".format(user_mention))
        return

    if (len(dst_addr) != 34):
        await client.send_message(message.channel, "{0}！アドレスがおかしいわね！！".format(user_mention))
        return

    try:
        amount   = _round_down8(params[2])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}！amount:{1}が数字じゃないわよ！！".format(user_mention, params[2]))
        return

    if amount < _round_down8(WITHDRAW_AMOUNT_MIN):
        await client.send_message(message.channel, "{0}！amount:{1:.8f}が最小値より少ないわ！！".format(user_mention, amount))
        return

    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, userid)
        if row is not None:
            # src アドレス取得
            src_addr = row[WalletNum.ADDR.value]
            src_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
        else:
            await client.send_message(message.channel, "{0}！あなたなんて知らないわ！！".format(user_mention))
            return

    contain_fee = amount + _round_down8(TRANSACTION_FEE)
    if src_balance < contain_fee: # 残高がamountより下だったらエラー
        await client.send_message(message.channel, "{0}！XSELが足りないようね！手数料が{3}必要よ！！balance:{1:.8f} XSEL / amount:{2:.8f} XSEL".format(user_mention, src_balance, amount, TRANSACTION_FEE))
        return

    sendAmount = amount * COIN
    p = Proxy()
    try :
        transaction = p.sendtoaddress(dst_addr, _str_integer(sendAmount))
    except bitcoin.rpc.JSONRPCError as ex:
        await client.send_message(message.channel, "{0}！失敗よ！！{1}".format(user_mention, ex))
        logger.warning("withdraw error id={0} name={1} address={2} amount={3} error={4}".format(userid, username, dst_addr, amount, ex))
        return

    logger.info("withdraw id={0} name={1} address={2} amount={3} error={4}".format(userid, username, dst_addr, amount, transaction))

    # 送金分を減算
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        src_after_balance = src_balance - contain_fee
        if not _update_balance(cursor, userid, src_after_balance):
            await client.send_message(message.channel, "{0}！失敗したようね！！".format(user_mention))
            return
        connection.commit()

    ################################
    wd_dst  = "**address**\r\n{0}\r\n".format(dst_addr)
    wd_am   = "**amount**\r\n{0:.8f} XSEL\r\n".format(amount)
    wd_tran   = "**transaction**\r\n{0}\r\n".format(transaction)
    disp_msg = wd_dst + wd_am + wd_tran
    await _disp_rep_msg( client, message, username, 'withdraw',disp_msg )
    ################################
    return


####################################################################################
# 未対応、未実装        info, deposit
####################################################################################

# ,deposit addr (amount)    TODO アドレスいる？自分のならいらない
# ウォレットからdiscord walletに送金します。
# ウォレットにXSELを入れるには、このアドレスに送金してください。
##########################################
# admin用
# cmd_admin_lstに設定されているユーザしか実行できない。
##########################################

# balanceに値を設定する
#ex) ,adminsend ironwood#7205 1000.0
async def _cmd_admin_send(client, message, params):
    if not params[0] == _CMD_STR_ADMIN_SEND:
        return

    # Decimalの計算:float禁止
    getcontext().traps[FloatOperation] = True

    src_user     = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)

    if not _is_admin_user(src_user):
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADMIN_SEND, message.author, message.content))

    if (len(params) != 3):
        await client.send_message(message.channel, "コマンドが間違えています.")
        return

    user_info = _get_usermention2member(client, params[1])
    if user_info is None:
        await client.send_message(message.channel, "ユーザがいません。2")
        return
    dst_userid = user_info.id
    try:
        amount  = _round_down8(params[2])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, params[2]))
        return

    dst_balance = _round_down8("0.0")
    # dst_pending = _round_down8("0.0")
    dst_username = ''
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row = _get_user_row(cursor, dst_userid)
        if row is not None:
            dst_balance  = _round_down8(str(row[WalletNum.BALANCE.value]))
            # dst_pending  = _round_down8(str(row[WalletNum.PENDING.value]))
            dst_username = row[WalletNum.USER.value]

            dst_balance += amount
            if dst_balance < _round_down8("0.0"):
                dst_balance = _round_down8("0.0")
            if not _update_balance(cursor, dst_userid, dst_balance):
                await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
                return
        else:
            await client.send_message(message.channel, "{0}様、残高が更新できませんでした。".format(user_mention))
            return
        connection.commit()

    ################################
    # 残高表示
    ################################
    bl_user     = "**所有者**\r\n<@{0}> 様\r\n".format(dst_userid)
    bl_balance  = "**残高**\r\n{0:.8f} XSEL\r\n".format(dst_balance)
    # bl_pending  = "**PENDING**\r\n{0} XSEL\r\n".format(dst_pending)
    disp_msg = bl_user +bl_balance
    await _disp_rep_msg( client, message,'残高(BALANCE)','残高更新しました。',disp_msg )
    ################################
    return

# 自分のbalanceに値を加算する。
# ,adminself 1000,0
async def _cmd_admin_self(client, message, params):
    if not params[0] == _CMD_STR_ADMIN_SELF:
        return

    # Decimalの計算:float禁止
    getcontext().traps[FloatOperation] = True

    src_username = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)

    if not _is_admin_user(src_username):
        return

    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADMIN_SELF, message.author, message.content))

    if (len(params) != 2):
        await client.send_message(message.channel, "コマンドが間違えています.")
        return
    try:
        amount  = _round_down8(params[1])
    except:
        # exceptionで戻る
        await client.send_message(message.channel, "{0}様、amount:{1}のパラメータが間違えているようです。".format(user_mention, params[1]))
        return

    src_balance = _round_down8("0.0")
    # src_pending = _round_down8("0.0")
    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        row    = _get_user_row(cursor, src_userid)
        if row is not None:
            src_balance = _round_down8(str(row[WalletNum.BALANCE.value]))
            # src_pending = _round_down8(str(row[WalletNum.PENDING.value]))
            src_balance += amount
            if src_balance < _round_down8("0.0"):
                src_balance = _round_down8("0.0")
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
    bl_user     = "**所有者**\r\n{0} 様\r\n".format(user_mention)
    bl_balance  = "**残高**\r\n{0:.8f} XSEL   \r\n".format(src_balance)
    # bl_pending  = "**PENDING**\r\n{0} XSEL\r\n".format(src_pending)
    # disp_msg = bl_user +bl_balance + bl_pending
    disp_msg = bl_user +bl_balance
    await _disp_rep_msg( client, message,'残高(BALANCE)','残高更新しました。',disp_msg )
    ################################
    return

# discord balance total xsel
# ,adminbalance
# discord上の総額を表示
async def _cmd_admin_balance(client, message, params):
    if not params[0] == _CMD_STR_ADMIN_BALANCE:
        return

    # Decimalの計算:float禁止
    getcontext().traps[FloatOperation] = True

    src_user     = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)

    if not _is_admin_user(src_user):
        return

    dbg_print("{0} {1}:{2}".format(_CMD_STR_ADMIN_SEND, message.author, message.content))

    if (len(params) != 1):
        await client.send_message(message.channel, "コマンドが間違えています.")
        return

    with closing(sqlite3.connect(DBNAME)) as connection:
        cursor = connection.cursor()
        # ---------------------------------------
        total_balance = _round_down8("0.0")
        select_sql = 'select * from ' + REG_TABLENAME
        cursor.execute(select_sql)
        while 1:
            dst_balance = _round_down8("0.0")
            dst_username = ''
            row = cursor.fetchone();
            if row is not None:
                dst_balance  = _round_down8(str(row[WalletNum.BALANCE.value]))
                dst_username = row[WalletNum.USER.value]
            else:
                break
            total_balance += dst_balance
    ################################
    totalb_src  = "**総額**\r\n{0:.8f} XSEL\r\n".format(total_balance)
    disp_msg = totalb_src
    await _disp_rep_msg( client, message,'discord wallet','結果を表示します。',disp_msg )
    ################################
    return

async def _cmd_version(client, message, params):
    if not params[0] == _CMD_STR_VERSION:
        return
    src_username = str(message.author)
    src_userid   = str(message.author.id)
    user_mention = str(message.author.mention)

    dbg_print("{0} {1}:{2}".format(_CMD_STR_VERSION, message.author, message.content))

    await client.send_message(message.channel, '```{0}```'.format(RELEASE_VERSION) )
    return

##########################################
# debug
##########################################
# ユーザ確認
# ,dbg members online
# ,dbg members all
async def _cmd_dbg_cmd(client, message, params):
    if not params[0] == _CMD_STR_DBG_CMD:
        return
    dbg_print("{0} {1}:{2}".format(_CMD_STR_DBG_CMD, message.author, message.content))

    send_ch = message.channel
    src_addr = ""
    print(len(params))
    if (len(params) < 3):
        await client.send_message(send_ch, "dbgコマンドが間違えている.")
        return
    # ,dbg members online
    # ,dbg members all
    if "members" == str(params[1]):
        if "online" == str(params[2]):
            members = client.get_all_members()
            # # onlineユーザ取得
            online_users = list(filter(lambda x: (x.bot == False) and (x.status == discord.Status.online), members))
            # # Member obj->mapでmember名->list->str->send
            await client.send_message(send_ch, str(list(map(str,online_users))))
        elif "idle" == str(params[2]):
            members = client.get_all_members()
            # # onlineユーザ取得
            online_users = list(filter(lambda x: (x.bot == False) and (x.status == discord.Status.idle), members))
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
# Utility(DB)
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
            + REG_TABLENAME + ' ({0} integer primary key, {1} varchar(64), {2} varchar(64), {3} text, {4} text, {5} text)'.format(COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE)
        print(create_table)
        cursor.execute(create_table)
        connection.commit()

# insert_user
def _insert_user(cursor, userid, username, address, balance, pending):

    # --------------------------
    balance = str(balance)
    pending = str(pending)
    # --------------------------

    update = False
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set {0}=?, {1}=?, {2}=?, {3}=?, {4}=? where {5}=?'.format(COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE, COLUMN_ID)
        cursor.execute(sql, (username, address, balance, pending, _getnowtime(), int(userid)))
        update = True
    else:
        sql = 'insert into ' + REG_TABLENAME + ' ({0}, {1}, {2}, {3}, {4}, {5}) values (?,?,?,?,?,?)'.format(COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING, COLUMN_LASTUPDATE)
        cursor.execute(sql, (int(userid), username, address, balance, pending, _getnowtime()))
    return update

# 残高更新
def _update_balance(cursor, userid, balance):
    update = False
    # --------------------------
    balance = str(balance)
    # --------------------------
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set {0}=?, {1}=? where {2}=?'.format(COLUMN_BALANCE, COLUMN_LASTUPDATE, COLUMN_ID)
        cursor.execute(sql, (balance, _getnowtime(), int(userid)))
        update = True
    return update

# username更新
def _update_username(cursor, userid, username):
    update = False
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set {0}=?, {1}=? where {2}=?'.format(COLUMN_USER, COLUMN_LASTUPDATE, COLUMN_ID)
        cursor.execute(sql, (username, _getnowtime(), int(userid)))
        update = True
    return update

# address更新
def _update_address(cursor, userid, address):
    update = False
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set {0}=?, {1}=? where {2}=?'.format(COLUMN_ADDRESS, COLUMN_LASTUPDATE, COLUMN_ID)
        cursor.execute(sql, (address, _getnowtime, int(userid)))
        update = True
    return update

# pending更新
def _update_pending(cursor, userid, pending):
    update = False
    # --------------------------
    pending = str(pending)
    # --------------------------
    if _is_exists_userid(cursor, userid):
        sql = 'update ' + REG_TABLENAME + ' set {0}=?, {1}=? where {2}=?'.format(COLUMN_PENDING, COLUMN_LASTUPDATE, COLUMN_ID)
        cursor.execute(sql, (pending, _getnowtime(), int(userid)))
        update = True
    return update

# exist userid True:exist / False:
def _get_user_row(cursor, userid):
    select_sql = 'select * from ' + REG_TABLENAME + ' where {0}=?'.format(COLUMN_ID)
    cursor.execute(select_sql, (int(userid),))
    # 見つかったものを返却
    return cursor.fetchone()

# exist user True:exist / False:
def _is_exists_userid(cursor, userid):
    select_sql = 'select * from ' + REG_TABLENAME + ' where {0}=?'.format(COLUMN_ID)
    cursor.execute(select_sql, (int(userid),))
    if cursor.fetchone() is None:
        return False
    else:
        return True

# exist user & address pare
def _is_exists_record(cursor, userid, user_name, address, balance, pending):
    # --------------------------
    balance = str(balance)
    pending = str(pending)
    # --------------------------
    select_sql = 'select * from ' + REG_TABLENAME + ' where {0}=? and {1}=? and {2}=? and {3}=? and {4}=?'.format(COLUMN_ID, COLUMN_USER, COLUMN_ADDRESS, COLUMN_BALANCE, COLUMN_PENDING)
    # select_sql = 'select * from ' + REG_TABLENAME + ' where id=?'
    cursor.execute(select_sql, (int(userid), user_name, address, balance, pending))
    if cursor.fetchone() is None:
        return False
    else:
        return True

def count_record(cursor):
    select_sql = 'select count(*) from ' + REG_TABLENAME
    cursor.execute(select_sql)
    count = cursor.fetchone()
    return count

def _dump_all(cursor):
    for row in cursor.execute("select * from " + REG_TABLENAME):
        print(row)

##########################################
# Utility:dicord user
##########################################

# debug private msg print
# async def _dump_all_private(client, message, cursor):
#     for row in cursor.execute("select * from " + REG_TABLENAME):
#         await client.send_message(message.author,str(row))

def _get_usermention2member(client, usermention):
    found_member = None
    # @<21839127398172937>とかできていることを想定する。
    user_id = usermention.strip('@<>')
    if False == user_id.isdigit():
        return found_member
    members = client.get_all_members()  # メンバ取得
    for member in members:
        if user_id == str(member.id):
            found_member = member
            break
    return found_member

# ユーザ名からmember Objを返す.
def _get_user2member(client, username):
    found_member = None
    members = client.get_all_members()  # メンバ取得
    for member in members:
        if username == str(member):
            found_member = member
            break
    return found_member

# admin user check
def _is_admin_user(user):
    admin_member = list(filter(lambda x: (x == user) , cmd_admin_lst))
    if (len(admin_member) > 0):
        return True
    return False

##########################################
# Utility:Decimal
##########################################

def _round_down8(value):
    # value = Decimal(value).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    value = Decimal(value).quantize(Decimal('0.00000000'), rounding=ROUND_DOWN)
    return value

def _str_round_down8(value):
    return "{:.8f}".format(value)

def _str_integer(value):
    return "{:.0f}".format(value)

##########################################
# 表示
##########################################
# コマンドに対する応答
async def _disp_rep_msg( client, message, disp_name, disp_title, disp_msg ):
    # # 埋め込みメッセージ
    msg = discord.Embed(title=disp_title, type="rich",description=disp_msg, colour=0x3498db)
    # TODO iconが挿入されないので後で確認
    msg.set_author(name=disp_name, icon_url=message.author.avatar_url)

    # ---------------------------------------------------------
    # selnのICONならこっち(seniのicon)
    # user_info = await client.get_user_info(441218236227387407)
    # msg.set_thumbnail(url=user_info.avatar_url)
    # ---------------------------------------------------------
    # 応答者のICONならこっち
#    msg.set_thumbnail(url=message.author.avatar_url)
    # ---------------------------------------------------------
    # msg.set_footer(text='###########')
    txt_msg = await client.send_message(message.channel, embed=msg)
    # await client.add_reaction(txt_msg,'👍')

# コンソールメッセージ
def dbg_print( msg_str ):
    print(msg_str)
    pass

def _getnowtime():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")