from flask import Flask, request
import requests
import sys
import os
import json
from Credentials import *
import time
import _thread
import urllib.request
app = Flask(__name__)



# ----
# vars
# ----
refreshRateMinutes = 2
refreshRateSeconds = 60 * refreshRateMinutes
percentageValue = 15
userList = ["1815874935130054"]
alertDictList = [{'ticker': "NEO", 'timer': 64}, {'ticker': 'HUSH', 'timer': 64}]

addTrigger = ["add"]
deleteTrigger = ["del", "delete"]
showTrigger = ["show", "show list"]
changePercentageValueTrigger = ["change", "change percentage", "change percentage to"]

CMC_URL = "https://api.coinmarketcap.com/v1/ticker/?limit=1000"
with urllib.request.urlopen(CMC_URL) as cmc_url:
    s = cmc_url.read()
CMCdata = json.loads(s)

quick_replies_list = [
    {
        "content_type": "text",
        "title": "show",
        "payload": "show",
    },
    {
        "content_type": "text",
        "title": "help",
        "payload": "help",
    }
]



# ----------
# extra defs
# ----------
def sliceWords(string, beginIndex, endIndex):
    stringList = string.split()
    stringList = stringList[beginIndex:endIndex]
    newString = ""
    for word in stringList:
        newString += word
        newString += " "
    newString = newString[0: len(newString) - 1]
    return newString



def isFloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False



# --------
# CMC defs
# --------
def refreshCMCData():
    with urllib.request.urlopen(CMC_URL) as url:
        global s, CMCData
        s = url.read()
    CMCData = json.loads(s)



def getCoinTickerList(dataList):
    coinList = []
    for coinDetails in dataList:
        coinName = coinDetails[u'symbol']
        coinList += [coinName]
    return coinList



def getCoinNameList(dataList):
    coinNameList = []
    for coinDetails in dataList:
        coinName = coinDetails[u'id']
        coinNameList += [coinName]
    return coinNameList



coinTickerList = getCoinTickerList(CMCdata)



def getCoinInfo(tickerOrName, data):
    if tickerOrName in getCoinTickerList(data):
        coin_info = next(coin for coin in data if coin[u'symbol'] == tickerOrName)
        return coin_info

    elif tickerOrName in getCoinNameList(data):
        coin_info = next(coin for coin in data if coin[u'id'] == tickerOrName)
        return coin_info



def getCoinInfoElement(ticker, aspect, data):
    coininfo = getCoinInfo(ticker, data)
    coininfoelement = coininfo[aspect]
    return coininfoelement



def getOneHourChange(ticker):
    return float(getCoinInfoElement(ticker, 'percent_change_1h', CMCdata))



def getCoinTickersFromDict(dict_list):
    coin_ticker_list = []
    for element in dict_list:
        coin_ticker_list += [element['ticker']]
    return coin_ticker_list



def addCoin(coin_ticker, dict_list):
    new_dict = {}
    coin_ticker_list = getCoinTickersFromDict(dict_list)
    if coin_ticker not in coin_ticker_list:
        new_dict['ticker'] = coin_ticker
        new_dict['timer'] = 64
        dict_list += [new_dict]



def deleteCoin(coin_ticker, dict_list):
    for index in range(len(dict_list)):
        if dict_list[index]['ticker'] == coin_ticker:
            dict_list.pop(index)
            break



def showAlertCoins(dict_list):
    bot_reply = ""
    coin_ticker_list = getCoinTickersFromDict(dict_list)
    for coin in coin_ticker_list:
        bot_reply += "{}\n".format(coin)
    bot_reply += "percentage: {}%".format(percentageValue)
    return bot_reply



def changePercentageValue(percentage_value):
    global percentageValue
    if isFloat(percentage_value):
        if float(percentage_value) > 0:
            percentageValue = float(percentage_value)



def resetTimer(dict):
    dict['timer'] = 0



def timerProgressor(dict):
    dict['timer'] += refreshRateMinutes



def checkIfPumped(dict_list):
    global userList
    for dict in dict_list:
        coin_ticker = dict['ticker']
        timer = dict['timer']
        one_hour_change = getOneHourChange(coin_ticker)

        if timer > 62:

            if abs(one_hour_change) > percentageValue and timer > 60:
                bot_reply = "{} changed {}%".format(coin_ticker, one_hour_change)
                for user in userList:
                    send_message(user, bot_reply)
                resetTimer(dict)

        elif timer < 66:
            timerProgressor(dict)


def threadOne():
    while True:
        print('Checked the percentages.')
        print(alertDictList)
        print(percentageValue)
        refreshCMCData()
        checkIfPumped(alertDictList)
        time.sleep(refreshRateSeconds)



@app.route('/', methods=['GET'])
def handle_verification():
    if request.args.get('hub.verify_token', '') == VERIFY_TOKEN:
        return request.args.get('hub.challenge', 200)
    else:
        return 'Error, wrong validation token'


@app.route('/', methods=['POST'])
def handle_messages():
    global userList
    data = request.get_json()
    log(data)

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    try:
                        message_text = messaging_event["message"]["text"]
                    except KeyError:
                        message_text = 'image'
                    
                    
                    
                    coinTicker = sliceWords(message_text, -1, None).upper()
                    newPercentageValue = sliceWords(message_text, -1, None)
                    newUser = sliceWords(message_text, -1, None)



                    # show alert coins
                    if message_text.lower() in showTrigger:
                        botReply = showAlertCoins(alertDictList)
                        send_message(sender_id, botReply)



                    # add coin
                    elif sliceWords(message_text, 0, -1).lower() in addTrigger:
                        refreshCMCData()
                        coinTickerList = getCoinTickerList(CMCdata)

                        if coinTicker in coinTickerList:
                            addCoin(coinTicker, alertDictList)
                            botReply = "Added {}. These are the coins you want an alert from:\n".format(coinTicker) + showAlertCoins(alertDictList)
                            send_message(sender_id, botReply)

                        else:
                            botReply = "That coin is not included"



                    # delete coin
                    elif sliceWords(message_text, 0, -1).lower() in deleteTrigger:
                        refreshCMCData()
                        coinTickerList = getCoinTickerList(CMCdata)

                        if coinTicker in coinTickerList:
                            deleteCoin(coinTicker, alertDictList)
                            botReply = "deleted {}. These are the coins you want an alert from:\n".format(coinTicker) + showAlertCoins(alertDictList)
                            send_message(sender_id, botReply)

                        else:
                            botReply = "That coin is not included"



                    # change percentage
                    elif sliceWords(message_text, 0, -1).lower() in changePercentageValueTrigger:
                        if isFloat(newPercentageValue):
                            changePercentageValue(newPercentageValue)
                            botReply = "The new percentage to get an alert is {}".format(percentageValue)
                            send_message(sender_id, botReply)



                    # update
                    elif message_text.lower() == 'update':
                        botReply = "Updated! I will be able to send again for the next 24 hours."
                        send_message(sender_id, botReply)



                    # help
                    elif message_text.lower() == 'help':
                        botReply = 'This bot will notify you when a coin pumps or drops below a certain percentage value.' \
                                    '\nThe bot can only send messages in a period 24 hours later than when it recieved the last message from you.' \
                                    '\n\n-You can add a coin to the watchlist by sending "add" and the ticker of that coin.' \
                                    '\n\n-You can delete a coin by typing "delete" and the ticker of that coin.' \
                                    '\n\n-You can show the coins the bot is watching by typing "show".' \
                                    '\n\n-You can change the value of the percentage by typing "change" or "change pecentage to" and the value you want it to have. For example "change percentage to 25".'
                        send_message(sender_id, botReply)



                    # test message
                    elif message_text.lower() == "test message":
                        for user in userList:
                            botReply = "test"
                            send_message(user, botReply)



                    # add user
                    elif sliceWords(message_text, 0, -1).lower() == "add user":
                        if newUser not in userList:
                            userList += [newUser]
                            botReply = "Added a new user"
                            send_message(sender_id, botReply)
                        print(userList)
                        



                    # default
                    else:
                        botReply = "Sorry, I do not understand this message."
                        send_message(sender_id, botReply)
              

                if messaging_event.get("delivery"):
                    pass

                if messaging_event.get("optin"):
                    pass

                if messaging_event.get("postback"):
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):
    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text,
            "quick_replies": quick_replies_list
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
    log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()

   
            
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    try:
        _thread.start_new_thread(threadOne, ())
        _thread.start_new_thread(app.run(host='0.0.0.0', port=port), ())
    
    except:
        print ("Error: unable to start thread")

    while 1:
        pass
