#########################################################################
#作成者:
#ダク
#目次:
# 1.コマンド
# 2.メッセージ処理
# 3.キャラクリエイト関連
# 4.ダイス処理
# 5.データベース操作
# 6.Json連携
# 8.たいせつなところ
#########################################################################
# 1.コマンド
#########################################################################
from __future__ import unicode_literals
from chara import Character
import discord # インストールした discord.py
import os
import time
import math
import random
import asyncio
import re
import sqlite3
import json
from contextlib import closing
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
import gspread
import chara


# Suppress noise about console usage from errors
#初期化NG
client = discord.Client() # 接続に使用するオブジェクト
sessionChannelList = []
keyword = 'hellowelps'
voice = None
numDL = 50
version = '0.2.2'
gfile = None

# 初期化OK
diceText = '' #ダイス用テキスト
diceTextList = []
isError = False #エラー判定
critical = -9999999
fumble = 999999999

# データベースアクセス
#########################################################################
# データベースファイルのパス
dbpath = 'session_db.sqlite'
# データベース接続とカーソル生成
connection = sqlite3.connect(dbpath)
# 自動コミットにする場合は下記を指定（コメントアウトを解除のこと）
# connection.isolation_level = None
cursor = connection.cursor()
#########################################################################


# 起動時に通知してくれる処理
@client.event
async def on_ready():
    global keyword
    global gfile
    print('ログインしました')
    print(client.user.name)
    print(client.user.id)
    print('---------')
    print('Hi. Trpg player. My app version is ' + version)
    gfile = getSheets()


@client.event
async def on_message(message):
  # BOTとメッセージの送り主が同じ人なら処理しない
  if client.user == message.author:
      return
  text = None
  text = str(message.content)
  text = text.replace('\n', ' ')
  text = text.split(' ')
  global sessionChannelList
  global keyword
  global player
  global voice
  global diceText
  global diceTextList
  global calcTypeList
  global isError
  global critical
  global fumbl
  global randomName
  global numDL
  global cursor
  await allInit()

  # 管理者コマンド
  if text[0] == ("!admin"):
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者"):
      dm = await message.author.create_dm()
      await dm.sendsend(sessionChannelList)

  # 管理者サーバ選定コマンド
  if text[0] == ("!adminInit"):
    if len(text) < 2:
      return
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者"):
      if text[1] != keyword:
        await message.channel.send("正しいトークンを入力してください。")
        return
      err = await tableCreate(message)
      if(err != 'success'):
        await message.channel.send("サーバのセッションリストの取得に失敗しました。")
        return
      await message.channel.send("サーバのセッションリストを初期化・取得しました。")

  # 管理者サーバ再起動コマンド
  if text[0] == ("!adminReboot"):
    if len(text) < 2:
      return
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者"):
      if text[1] != keyword:
        await message.channel.send("正しいトークンを入力してください。")
        return
      await adminInit()
      await message.channel.send("サーバを再起動しました。")

  # 管理者用終了コマンド
  if text[0] == ("!adminEnd"):
    if len(text) < 2:
      return
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者"):
      if text[1] != keyword:
        await message.channel.send("正しいトークンを入力してください。")
        return
      await adminInit()
      print(sessionChannelList)
      await message.channel.send("TRPGBotを終了します。")
      if voice is not None and voice.is_playing():
        voice.stop()
      if voice is not None and voice.is_connected():
        await voice.disconnect(force = True)
      await client.close()
      sys.exit()
      return

  # ゲームマスター宣言
  if text[0].startswith('/gmstart'):
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者") or discord.utils.get(message.author.roles, name="ゲームマスター"):
      err = await setGM(message)
      if(err != 'success'):
        await message.channel.send(err)
        return
      await message.channel.send(message.author.name + "さんがこのセッションのゲームマスターとなりました。")

  # ゲームマスター終了
  if text[0].startswith('/gmend'):
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者") or discord.utils.get(message.author.roles, name="ゲームマスター"):
      err = await delGM(message)
      if(err != 'success'):
        await message.channel.send(err)
        return
      await message.channel.send("この部屋は空き部屋となりました。10秒後に全メッセージが破棄されます。")
      time.sleep(10)
      await chatDelete(message)

  # 削除コマンド
  if message.content.startswith("!delchat"):
    #役職比較
    if discord.utils.get(message.author.roles, name="管理者") or discord.utils.get(message.author.roles, name="準管理者"):
      if message.channel.name.startswith("セッション") or message.channel.name.startswith("設定"):
        await chatDelete(message)
      else:
        await message.channel.send("メッセージを削除できるチャンネルではありません")
    elif discord.utils.get(message.author.roles, name="ゲームマスター"):
      err = await selectGM(message)
      if(err != 'success'):
        await message.channel.send(err)
        return
      await chatDelete(message)
    else:
      # エラーメッセージを送ります
      await message.channel.send("管理者権限がありません。管理者に問い合わせてください。")
    return

  # 曲停止
  if text[0] == ('/bgmStop') or text[0] == ('/stop') or text[0] == ('!s'):
    err = await selectGM(message)
    if(err != 'success'):
      await message.channel.send(err)
      return
    if voice is not None and voice.is_playing():
      voice.stop()
    if voice is not None and voice.is_connected():
      await voice.disconnect(force = True)
    return

  # 曲再生
  if text[0] == ('/bgm'):
    try:
      if len(text) < 1:
        return
      err = await selectGM(message)
      if(err != 'success'):
        await message.channel.send(err)
        return
      for voiceChannel in message.guild.voice_channels:
        if message.channel.name == voiceChannel.name:
          if voice is not None and voice.is_playing():
            voice.stop()
          if voice is not None and voice.is_connected():
            await voice.move_to(voiceChannel)
          else:
            voice = await voiceChannel.connect()
          voice.play(discord.FFmpegPCMAudio("bgm/" + str(text[1]) + '.mp3'), after=lambda e: print('done', e))
    except Exception as e:
      dm = await message.author.create_dm()
      await dm.send('BGM再生でエラーが発生しました。キーワードが間違っている可能性があります。管理者に問い合わせてください。')
      await dm.send(e)
      print(e)
    return

  # クトゥルフ用ダイスポット
  if text[0].startswith('CCB'):
    ccb = text[0].replace('CCB', '1d100')
    critical = 5
    fumble = 96
    await result(message.channel, ccb, message.author.mention)
    return

  # クトゥルフ用ダイスポット
  if text[0].startswith('CC') and not text[0].startswith('CCB'):
    cc = text[0].replace('CC', '1d100')
    critical = 1
    fumble = 100
    await result(message.channel, cc, message.author.mention)
    return

  # 組み合わせロール
  if text[0].startswith('cbr('):
    cbr = text[0].replace('cbr(', '')
    cbr = cbr.replace(')', '')
    cbrList = cbr.split(',')
    if len(cbrList) < 1:
      return
    await multiResult(message.channel, '1d100', cbrList, message.author.mention)
    return

  # 対抗ロール
  if text[0].startswith('res('):
    res = text[0].replace('res(', '')
    res = res.replace(')', '')
    resList = res.split('-')
    if len(resList) != 2 or resList[0].isdecimal() == False or resList[0].isdecimal() == False:
      return
    oppositionint = int(resList[0]) - int(resList[1])
    oppositionint = 50 + (oppositionint * 5)
    await result(message.channel, '1d100<=' + str(oppositionint), message.author.mention)
    return

  # チョイスコマンド
  if text[0].startswith('choice['):
    choice = text[0].replace('choice[', '')
    choice = choice.replace(']', '')
    choiceList = choice.split(',')
    if len(choiceList) < 1:
      return
    await message.channel.send('(CHOICE[' + ','.join(choiceList) + ']) → **' + random.choice(choiceList) +'**')
    return

  # キャラクリエイト
  if text[0] == ('/c'):
    if len(text) < 2:
      return
    if message.channel.name.startswith("セッション") or message.channel.name.startswith("設定"):
      if text[1] == ('coc'):
        statusNameList = 'STR,CON,POW,DEX,APP,SIZ,INT,EDU'
        await statusCreate(message,'3d6,3d6,3d6,3d6,3d6,2d6+6,2d6+6,3d6+3', statusNameList)
      return

  # 通常ダイスボット シークレットダイス付き
  if re.match('^[sSｓＳ]?([1-9１-９]+[0-9０-９]*[-+ー＋])?[1-9１-９]+[0-9０-９]*[dDｄＤ]{1}[1-9１-９]+[0-9０-９]*', text[0]):
    comSend = message.channel
    isSecret = False
    base = text[0].translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))
    if text[0].startswith("-") or text[0].startswith("ー") or text[0].startswith("+") or text[0].startswith("＋"):
      text[0] = "0" + text[0]
    if text[0].startswith("s") or text[0].startswith("S"):
      comSend = await message.author.create_dm()
      isSecret = True
      base = base.replace('s', '')
      base = base.replace('S', '')
    if len(text) < 3:
      text.append('1')
    if text[1].isdecimal() == True:
      intLapNum = int(text[1])
      if(intLapNum > 10):
        return
      if(intLapNum == 1):
        await result(comSend, base, message.author.mention)
        if isSecret == True:
          await message.channel.send('シークレットダイス')
        return
      for i in range(intLapNum):
        if message.channel.name.startswith("セッション") or message.channel.name.startswith("設定"):
          await result(comSend, base, message.author.mention + ' ' + str(i + 1) + '回目')
    else:
      await result(comSend, base, message.author.mention)
    return

  #チャットパレット機能
  if text[0].startswith("https://charasheet.vampire-blood.net/") or text[0].startswith('charasheet.vampire-blood.net/') or text[0].startswith("!https://charasheet.vampire-blood.net/") or text[0].startswith('!charasheet.vampire-blood.net/'):
    koukaiFlg = False
    if text[0].startswith('!'):
      text[0] = text[0].replace('!', '')
      koukaiFlg = True
    json = chara.create(text[0])
    if json == 'NoN':
      res = await getCreateDataJson(text[0])
      json = chara.noLoadCreate(res)
    data = None
    data = chara.Character(json)
    if(data.gamemode != 'coc'):
      return
    parrets = chara.prmCreate(data)
    parretText = message.author.mention + '  名前:' + data.name
    for parret in parrets:
      parretText = parretText + '\n' + parret
    if koukaiFlg == False:
      dm = await message.author.create_dm()
      await dm.send(parretText)
    else:
      await message.channel.send(parretText)
    await createDataJson(json, text[0])


    # テスト用
  if text[0] == ('/timeset'):
    # chara.create(text[1])
    await setCharaSheet(str(message.author.id), str(message.author.name))


  # テスト用
  if text[0] == ('/test'):
    # chara.create(text[1])
    await setCharaSheet(str(message.author.id), str(message.author.name))


  # テスト用
  if text[0] == ('/test2'):
    json = chara.create(text[1])
    if text[1].startswith("https://charasheet.vampire-blood.net/"):
      text[1] = text[1].replace('https://charasheet.vampire-blood.net/', '')
    if text[1].startswith("http://charasheet.vampire-blood.net/"):
      text[1] = text[1].replace('http://charasheet.vampire-blood.net/', '')
    text[1] = text[1].replace('.js', '')
    await setCharaSheet(str(json),text[1])
    print(await getCharactor(text[1]))

#########################################################################
# 2.メッセージ処理
#########################################################################
# メッセージ削除処理
async def chatDelete(message):
  # メッセージ取得
  await message.channel.purge()
  time.sleep(0.5)
  await message.channel.send('いつでもゲームを開始できます！')
#########################################################################
# 3.キャラクリエイト関連
#########################################################################
#ステータスクリエイト
async def statusCreate(message, statsList, statsNameList):
  global diceText
  statsList = statsList.split(',')
  statsNameList = statsNameList.split(',')
  sendText = message.author.mention
  for i in range(len(statsList)):
    await result(message.channel, statsList[i], statsNameList[i], True)
    sendText = sendText + '\n' + diceText
    await allInit()
  await message.channel.send(sendText)
#########################################################################
# 4.ダイス処理
#########################################################################
# ダイスチャット
async def result(message, dice, target, noSend=False):
  global diceText
  global diceTextList
  global critical
  global fumble
  global isError
  totalNum = await comparison(message, dice)
  if isError == True:
    return
  diceText = target + ' (' + dice + ') → ' + diceText
  if totalNum <= critical and critical > 0:
    diceText += ' **クリティカル**'
  if totalNum >= fumble and fumble <= 100 :
    diceText += ' **ファンブル**'
  if noSend == True:
    return
  await message.send(diceText)
  await allInit()

# 組み合わせロール
async def multiResult(message, dice, skill, target):
  global diceText
  global diceTextList
  global critical
  global fumble
  global isError
  skillJudgList = []
  lastJudg = '成功'
  totalNum = await comparison(message, dice)
  for i in range(len(skill)):
    if skill[i].isdecimal() == False:
      await isErrorRoute()
      return
    intSkill = calcTarget(skill[i])
    if(totalNum <= intSkill):
      skillJudgList.append('成功')
    else:
      skillJudgList.append('失敗')
      lastJudg = '失敗'
  if isError == True:
    return
  diceText = target + ' (' + dice + '<=' + ','.join(skill) + ') → ' + diceText + '[' + ','.join(skillJudgList) + ']' + ' → **' + lastJudg + '**'
  if totalNum == critical and critical > 0:
    diceText += ' **クリティカル**'
  if totalNum == fumble and fumble <= 100:
    diceText += ' **ファンブル**'
  await message.send(diceText)
  await allInit()

# 比較ロール用
async def comparison(message, text):
  global diceText
  global diceTextList
  comDice = None
  comparsionType = None
  if '<=' in text:
    comDice = text.split('<=')
    comparsionType = 0
  elif '<' in text:
    comDice = text.split('<')
    comparsionType = 1
  elif '>=' in text:
    comDice = text.split('=>')
    comparsionType = 2
  elif '>' in text:
    comDice = text.split('>')
    comparsionType = 3
  if comDice is not None:
    comDice[1] = calcTarget(comDice[1])
    if comDice[1].isdecimal() == False:
      await isErrorRoute()
      return 0
    text = comDice[0]
  totalNum = await calcDice(message, text)
  if comDice is None:
    return totalNum
  comDice[1] = int(comDice[1])
  if comparsionType == 0:
    if totalNum <= comDice[1]:
      diceText = diceText + ' → 成功'
    else:
      diceText = diceText + ' → 失敗'
  if comparsionType == 1:
    if totalNum < comDice[1]:
      diceText = diceText + ' → 成功'
    else:
      diceText = diceText + ' → 失敗'
  if comparsionType == 2:
    if totalNum >= comDice[1]:
      diceText = diceText + ' → 成功'
    else:
      diceText = diceText + ' → 失敗'
  if comparsionType == 3:
    if totalNum > comDice[1]:
      diceText = diceText + ' → 成功'
    else:
      diceText = diceText + ' → 失敗'
  return totalNum


# 複数ダイス計算
async def calcDice(message, text):
  global diceText
  global diceTextList
  global calcTypeList
  dices = text.split('+')
  totalNum = 0
  for dice in dices:
    minusDices = dice.split('-')
    if len(minusDices) > 1:
      index = 0
      for minusDice in minusDices:
        if index == 0:
          totalNum = await calc(totalNum, minusDice, '+')
        else:
          totalNum = await calc(totalNum, minusDice, '-')
        index = index + 1
    else:
      totalNum = await calc(totalNum, dice, '+')
  calcTypeList[0] = ''
  j = 0
  for addDiceText in diceTextList:
    diceText = diceText + calcTypeList[j] + addDiceText
    j = j + 1
  diceText = diceText + ' → **' + str(totalNum) +'**'
  return totalNum

async def calc(totalNum,dice,calcType):
  global diceText
  global diceTextList
  global calcTypeList
  calcDice = []
  calcTypeList.append(calcType)
  if 'd' in dice:
    calcDice = dice.split('d')
  if 'D' in dice:
    calcDice = dice.split('D')
  if len(calcDice) > 2:
    await isErrorRoute()
    return
  if len(calcDice) == 2:
    if calcDice[0].isdecimal() == False or calcDice[1].isdecimal() == False:
      await isErrorRoute()
      return 0
    throw = int(calcDice[0])
    diceMax = int(calcDice[1])
    if(throw > 100 and diceMax > 1000):
      await isErrorRoute()
      return 0
    num = await randomDice(throw,diceMax)
    if calcType == '+':
      totalNum = totalNum + num
    if calcType == '-':
      totalNum = totalNum - num
  else:
    if dice.isdecimal() == False:
      await isErrorRoute()
      return 0
    if calcType == '+':
      totalNum = totalNum + int(dice)
    if calcType == '-':
      totalNum = totalNum - int(dice)
    diceTextList.append(dice)
  return totalNum

# ダイス計算
async def randomDice(throw, diceMax):
  global diceText
  global diceTextList
  dice = []
  totalNum = 0
  for i in range(throw):
    num = random.randint(1,diceMax)
    dice.append(num)
  totalNum = sum(dice)
  diceTextList.append(str(totalNum) + '[' + ','.join(map(str, dice)) + ']')
  return totalNum

#目標値計算
def calcTarget(target):
  calcType = -1
  try:
    if '+' in target:
      diviTarget = target.split('+')
      return str(int(diviTarget[0]) + int(diviTarget[1]))
    if '-' in target:
      diviTarget = target.split('-')
      return str(int(diviTarget[0]) - int(diviTarget[1]))
    if '*' in target:
      diviTarget = target.split('*')
      return str(int(diviTarget[0]) * int(diviTarget[1]))
    if '/' in target:
      diviTarget = target.split('/')
      return str(math.floor(int(diviTarget[0]) / int(diviTarget[1])))
    return target
  except (ZeroDivisionError, TypeError, ValueError) as e:
    retTarget = re.sub(r"[+-*/]", "", target)
    return retTarget[0]

#########################################################################
# 5.データベース操作
#########################################################################
gmselectsql = 'SELECT GameMaster FROM session WHERE TEXT_SESSION_ID=?'
allsessionSelect = 'SELECT GameMaster FROM session'
updatesql = 'UPDATE session SET GameMaster=? WHERE TEXT_SESSION_ID=?'

# 初期テーブル作成
async def tableCreate(message):
  global cursor
  # エラー処理（例外処理）
  try:
    # CREATE
    cursor.execute("DROP TABLE IF EXISTS session")
    cursor.execute(
      "CREATE TABLE IF NOT EXISTS session (id INTEGER PRIMARY KEY AUTOINCREMENT, TEXT_SESSION_ID INT, TEXT_SESSION_NAME TEXT, VOICE_SESSION_ID INT, GameMaster TEXT)")
    connection.commit()
    for channel in message.guild.text_channels:
      if channel.name.startswith("セッション") or channel.name.startswith("設定"):
        voiceChannelData = None
        for voiceChannel in message.guild.voice_channels:
          if channel.name == voiceChannel.name:
            session = (channel.id, channel.name, voiceChannel.id, '',)
            cursor.execute("INSERT INTO session(TEXT_SESSION_ID, TEXT_SESSION_NAME, VOICE_SESSION_ID, GameMaster) VALUES (?,?,?,?)", session)
    connection.commit()
    cursor.execute('SELECT * FROM session ORDER BY id')
    res = cursor.fetchall()
    print(res)
    return 'success'
  except sqlite3.Error as e:
    print('sqlite3.Error occurred:', e.args[0])
    return 'err'

# GM登録処理
async def setGM(message):
  global cursor
  try:
    cursor.execute(gmselectsql, (message.channel.id,))
    res = cursor.fetchall()
    print(res)
    if '' in res[0]:
      cursor.execute(allsessionSelect)
      res = cursor.fetchall()
      print(res)
      for i in range(len(res)):
        if message.author.name in res[i]:
          raise sqlite3.Error('あなたは既に他のセッションのゲームマスターです。')
      cursor.execute(updatesql, (message.author.name, message.channel.id))
      connection.commit()
    else:
      raise sqlite3.Error('既にこのセッションにはゲームマスターがいます。')
    return 'success'
  except sqlite3.Error as e:
    print('sqlite3.Error occurred:', e)
    return e

# GM削除処理
async def delGM(message):
  global cursor
  try:
    cursor.execute(gmselectsql, (message.channel.id,))
    res = cursor.fetchall()
    print(res)
    if message.author.name in res[0]:
      cursor.execute(updatesql, ('', message.channel.id))
      connection.commit()
    else:
      raise sqlite3.Error('このセッションのGMではない為、削除できません。')
    return 'success'
  except sqlite3.Error as e:
    print('sqlite3.Error occurred:', e)
    return e

# GM情報取得
async def selectGM(message):
  global cursor
  try:
    cursor.execute(gmselectsql, (message.channel.id,))
    res = cursor.fetchall()
    print(res)
    if message.author.name in res[0]:
      return 'success'
    else:
      raise sqlite3.Error('このセッションのGMではありません。')
  except sqlite3.Error as e:
    print('sqlite3.Error occurred:', e)
    return e

#########################################################################
# 6.Json連携
#########################################################################
# スプレッドシート操作
def getSheets():
  scopes = ['']
  json_file = './8.json'#OAuth用クライアントIDの作成でダウンロードしたjsonファイル
  credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scopes=scopes)
  http_auth = credentials.authorize(Http())
  # スプレッドシート用クライアントの準備
  doc_id = ''#これはスプレッドシートのURLのうちhttps://docs.google.com/spreadsheets/d/以下の部分です
  client = gspread.authorize(credentials)
  gfile   = client.open_by_key(doc_id)#読み書きするgoogle spreadsheet
  return gfile

#スプレッドシート用データ整形
async def createDataJson(sheetJson, url):
  url = chara.urlIDExtract(url)
  await setCharaSheet(json.dumps(sheetJson),url)

#スプレッドシート用データ整形
async def getCreateDataJson(url):
  url = chara.urlIDExtract(url)
  json = await getCharactor(url)
  return json

# スプレッドシート新規追加
async def setCharaSheet(sheetJson, sheetId):
  print(gfile)
  mainSheet = gfile.sheet1
  cell_list = mainSheet.range('A1:A1000')
  index = 1
  for cell in cell_list:
    if cell.value == sheetId:
      break
    elif cell.value == '':
      cell.value = sheetId
      break
    index = index + 1
  mainSheet.update_acell('B' + str(index), sheetJson)
  mainSheet.update_cells(cell_list)

# スプレッドシートキャラ取得
async def getCharactor(sheetId):
  worksheet = gfile.sheet1
  cell_list = worksheet.range('A1:A1000')
  index = 1
  for cell in cell_list:
    if cell.value == sheetId:
      break
    index = index + 1
  return worksheet.acell('B' + str(index)).value

# 旧スプレッドシートキャラ取得
#async def getTestaaaaa(sheetName):
#  worksheet = gfile.worksheet(sheetName)
#  charactor = {}
#  #技能名カラム
#  cell_keys = worksheet.col_values(1)
#  #合計値カラム
#  cell_values = worksheet.col_values(2)
#  for k,v in zip(cell_keys, cell_values):
#    charactor[k] = v
#  return charactor
#########################################################################
# 8.たいせつなところ
#########################################################################
# エラー判定
async def isErrorRoute():
  global isError
  isError = True
  await allInit()
# 初期化
async def allInit():
  global diceText
  global diceTextList
  global calcTypeList
  global critical
  global fumble
  global isError
  diceText = ''
  diceTextList = []
  calcTypeList = []
  critical = -9999999
  fumble = 999999999
  isError = False

# 管理者初期化
async def adminInit():
  global voice
  global numDL
  numDL = 50
  if voice is not None and voice.is_playing():
    voice.stop()
  if voice is not None and voice.is_connected():
    await voice.disconnect(force = True)
#########################################################################

# client.run('YOU_ID')

# botの接続と起動
# （tokenにはbotアカウントのアクセストークンを入れてください）

# 開発用
client.run('YOU_ID')
