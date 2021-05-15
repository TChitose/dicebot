import json
import copy
import urllib.request

#########################################################################
# 1. 初期設定　
#########################################################################
stateList = ['STR','CON','POW','DEX','APP','SIZ','INT','EDU','HP','MP']
statePoint = []
abilityList = []
abilityPoint = []
nameSentou = ['回避','キック','組み付き','こぶし（パンチ）','頭突き','投擲','マーシャルアーツ','拳銃','サブマシンガン','ショットガン','マシンガン','ライフル']
nameTansaku = ['応急手当','鍵開け','隠す','隠れる','聞き耳','忍び歩き','写真術','精神分析','追跡','登攀','図書館','目星']
nameKoudou = ['運転','機械修理','重機械操作','乗馬','水泳','製作','操縦','跳躍','電気修理','ナビゲート','変装']
nameKoushou = ['言いくるめ','信用','説得','値切り','母国語']
nameChishiki = ['医学','オカルト','化学','クトゥルフ神話','芸術','経理','考古学','コンピューター','心理学','人類学','生物学','地質学','電子工学','天文学','博物学','物理学','法律','薬学','歴史']

#########################################################################
# 2. get
#########################################################################
def getStatePoint():
    return statePoint

def getAbilityList():
    return abilityList

def getAbilityPoint():
    return abilityPoint
#########################################################################
# 3. キャラ作成
#########################################################################

def create(url):
    try:
        url.startswith("https://charasheet.vampire-blood.net/") or url.startswith('charasheet.vampire-blood.net/')
        if 'http' not in  url:
            url = 'https://' + url
        if '.js' not in url:
            url = url + '.js'
        jsn = None
        res = urllib.request.urlopen(url)
        jsn = json.loads(res.read().decode('utf-8'))
        return jsn
    except urllib.error.HTTPError as e:
        return "NoN"
    except sqlite3.Error as e:
        print('sqlite3.Error occurred:', e)
        return e

def noLoadCreate(res):
    try:
        jsn = json.loads(res)
        return jsn
    except sqlite3.Error as e:
        print('sqlite3.Error occurred:', e)
        return e

#キャラシURLからID抜き取り整形
def urlIDExtract(url):
    if url.startswith("https://charasheet.vampire-blood.net/"):
        url = url.replace('https://charasheet.vampire-blood.net/', '')
    if url.startswith("http://charasheet.vampire-blood.net/"):
        url = url.replace('http://charasheet.vampire-blood.net/', '')
    url = url.replace('.js', '')
    return url


#########################################################################
# 4. キャラ習得
#########################################################################
class Character:
    def __init__(self, json):
        global nameSentou
        global nameTansaku
        global nameKoudou
        global nameKoushou
        global nameChishiki
        self.gamemode = json['game']
        self.name = json['pc_name']         #名前
        self.shuzoku = json['shuzoku']      #職業
        self.age = json['age']              #年齢
        self.sex = json['sex']              #性別
        self.memo = json['pc_making_memo']  #メモ
        self.str = json['NP1']
        self.con = json['NP2']
        self.pow = json['NP3']
        self.dex = json['NP4']
        self.app = json['NP5']
        self.siz = json['NP6']
        self.int = json['NP7']
        self.edu = json['NP8']
        self.hp = json['NP9']
        self.mp = json['NP10']
        self.luck = json['NP11']
        self.know = json['NP12']
        self.san = json['SAN_Left']         #現在SAN
        self.sanMax = json['SAN_Max']       #最大SAN
        self.sanDenger = json['SAN_Danger'] #発狂SAN
        self.baseSentou = json['TBAD']      #初期値-戦闘技能
        self.totalSentou = json['TBAP']     #合計値-戦闘技能
        self.baseTansaku = json['TFAD']     #初期値-探索技能
        self.totalTansaku = json['TFAP']    #合計値-探索技能
        self.baseKoudou = json['TAAD']      #初期値-行動技能
        self.totalKoudou = json['TAAP']     #合計値-行動技能
        self.baseKoushou = json['TCAD']     #初期値-交渉技能
        self.totalKoushou = json['TCAP']    #合計値-交渉技能
        self.baseChishiki = json['TKAD']    #初期値-知識技能
        self.totalChishiki = json['TKAP']   #合計値-知識技能
        self.untenKoudou = json['unten_bunya']
        self.seisakuKondou = json['seisaku_bunya']
        self.soujuuKoudou = json['main_souju_norimono']
        self.bokokugoKoushou = json['mylang_name']
        self.geijutuChishiki = json['geijutu_bunya']
        json.setdefault('TBAName', [])
        json.setdefault('TFAName', [])
        json.setdefault('TAAName', [])
        json.setdefault('TCAName', [])
        json.setdefault('TKAName', [])
        self.inteSentou = addGinou(nameSentou,json['TBAName'])
        self.inteTansaku = addGinou(nameTansaku,json['TFAName'])
        self.inteKoudou = addGinou(nameKoudou,json['TAAName'])
        self.inteKoushou = addGinou(nameKoushou,json['TCAName'])
        self.inteChishiki = addGinou(nameChishiki,json['TKAName'])

def addGinou(copylist,datas):
    deepList = copy.deepcopy(copylist)
    for data in datas:
        deepList.append(data)
    return deepList


#########################################################################
# 5. データ操作
#########################################################################
def prmCreate(json):
    parret = []
    for i in range(len(json.inteSentou)):
        if(json.totalSentou[i] != json.baseSentou[i]):
            parret.append('CCB<='+ json.totalSentou[i] + ' '+ json.inteSentou[i])

    for i in range(len(json.inteTansaku)):
        if(json.totalTansaku[i] != json.baseTansaku[i]):
            parret.append('CCB<='+ json.totalTansaku[i] + ' '+ json.inteTansaku[i])

    for i in range(len(json.inteKoudou)):
        if(json.totalKoudou[i] != json.baseKoudou[i]):
            if(json.inteKoudou[i] == '運転'):
                json.inteKoudou[i] = json.inteKoudou[i] + '(' + json.untenKoudou + ')'
            if(json.inteKoudou[i] == '製作'):
                json.inteKoudou[i] = json.inteKoudou[i] + '(' + json.seisakuKondou + ')'
            if(json.inteKoudou[i] == '操縦'):
                json.inteKoudou[i] = json.inteKoudou[i] + '(' + json.soujuuKoudou + ')'
            parret.append('CCB<='+ json.totalKoudou[i] + ' '+ json.inteKoudou[i])
    
    for i in range(len(json.inteKoushou)):
        if(json.totalKoushou[i] != json.baseKoushou[i]):
            if(json.inteKoushou[i] == '母国語'):
                json.inteKoushou[i] = json.inteKoushou[i] + '(' + json.bokokugoKoushou + ')'
            parret.append('CCB<='+ json.totalKoushou[i] + ' '+ json.inteKoushou[i])
    
    for i in range(len(json.inteChishiki)):
        if(json.totalChishiki[i] != json.baseChishiki[i]):
            if(json.inteChishiki[i] == '芸術'):
                json.inteChishiki[i] = json.inteChishiki[i] + '(' + json.geijutuChishiki + ')'
            parret.append('CCB<='+ json.totalChishiki[i] + ' '+ json.inteChishiki[i])
    return parret