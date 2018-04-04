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
import gspread
from oauth2client.service_account import ServiceAccountCredentials



# -------------------------
# Google Spreadsheets prep
# -------------------------
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

sheet_coin = client.open('coins').sheet1
sheet_FBIDs = client.open('FB IDs').sheet1
sheet_percentage = client.open('percentage').sheet1



# ----
# vars
# ----
refreshRateMinutes = 2
refreshRateSeconds = 60 * refreshRateMinutes

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
        "title": "update",
        "payload": "update",
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



def nbRows(sheet):
    nb_rows = len(sheet.get_all_records()) + 1
    return nb_rows



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



def getUserList():
    global sheet_FBIDs
    sheet_FBIDs_data = sheet_FBIDs.get_all_records()
    fb_id_list = []
    for element in sheet_FBIDs_data:
        fb_id_list += [element['user']]
    return fb_id_list



def addUser(user_id):
    fb_id_list = getUserList()
    if user_id not in fb_id_list:
        new_row = [str(user_id)]
        sheet_FBIDs.append_row(new_row)

        

def deleteUser(user_id):
    global sheet_FBIDs
    sheet_FBIDs_data = sheet_FBIDs.get_all_records()

    for program_index in range(len(sheet_FBIDs_data)):
        sheet_index = program_index + 2

        if sheet_FBIDs_data[program_index]['user'] == user_id:
            sheet_FBIDs.delete_row(sheet_index)
            break

            
            
def getTimerWithTicker(ticker, sheet):
    sheet_data = sheet.get_all_records()

    for program_index in range(len(sheet_data)):
        sheet_index = program_index + 2
        if sheet_data[program_index]['ticker'] == ticker:
            timer = sheet_data[program_index]['timer']
            return float(timer)



def setTimerWithTicker(ticker, new_timer, sheet):
    sheet_data = sheet.get_all_records()

    for program_index in range(len(sheet_data)):
        sheet_index = program_index + 2
        if sheet_data[program_index]['ticker'] == ticker:
            sheet.update_cell(sheet_index, 2, new_timer)



def getPercentageValue():
    global sheet_percentage
    sheet_percentage_data = sheet_percentage.get_all_records()
    percentage = sheet_percentage_data[0]['percentage']
    return float(percentage)



def setPercentageValue(new_percentage):
    global sheet_percentage
    sheet_percentage.update_cell(2, 1, new_percentage)        
        
       
    
def getCoinTickersFromDict(dict_list):
    coin_ticker_list = []
    for element in dict_list:
        coin_ticker_list += [element['ticker']]
    return coin_ticker_list



def addCoinData(ticker, sheet):
    sheet_data = sheet.get_all_records()
    coin_ticker_list = getCoinTickersFromDict(sheet_data)
    if ticker not in coin_ticker_list:
        new_row = [ticker, 64]
        sheet.append_row(new_row)



def deleteCoinData(ticker, sheet):
    sheet_data = sheet.get_all_records()

    for program_index in range(len(sheet_data)):
        sheet_index = program_index + 2

        if sheet_data[program_index]['ticker'] == ticker:
            sheet.delete_row(sheet_index)
            break



def showAlertCoins(sheet):
    bot_reply = "The coins I'm currently watching are:\n"
    sheet_data = sheet.get_all_records()
    coin_ticker_list = getCoinTickersFromDict(sheet_data)
    for coin in coin_ticker_list:
        bot_reply += "{}\n".format(coin)
    bot_reply += "percentage: {}%".format(getPercentageValue())
    return bot_reply



def resetTimer(ticker, sheet):
    setTimerWithTicker(ticker, 0, sheet)



def timerProgressor(ticker, sheet):
    current_timer = getTimerWithTicker(ticker, sheet)
    new_timer = current_timer + refreshRateMinutes
    setTimerWithTicker(ticker, new_timer, sheet)



def checkIfPumped(sheet):
    sheet_data = sheet.get_all_records()

    for dict in sheet_data:
        coin_ticker = dict['ticker']
        timer = dict['timer']
        one_hour_change = getOneHourChange(coin_ticker)

        if timer > 62:

            if abs(one_hour_change) > getPercentageValue() and timer > 60:
                bot_reply = "{} changed {}%".format(coin_ticker, one_hour_change)
         
                for user in getUserList():
                    send_message(user, bot_reply)
                resetTimer(coin_ticker, sheet)

        elif timer < 66:
            timerProgressor(coin_ticker, sheet)


def threadOne():
    while True:
        print('Checked the percentages.')
        print(sheet_coin.get_all_records())
        print(getPercentageValue())
        refreshCMCData()
        checkIfPumped(sheet_coin)
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
                    userID = sliceWords(message_text, -1, None)



                    # show alert coins
                    if message_text.lower() in showTrigger:
                        botReply = showAlertCoins(sheet_coin)
                        send_message(sender_id, botReply)



                    # add coin
                    elif sliceWords(message_text, 0, -1).lower() in addTrigger:
                        refreshCMCData()
                        coinTickerList = getCoinTickerList(CMCdata)

                        if coinTicker in coinTickerList:
                            addCoinData(coinTicker, sheet_coin)
                            botReply = "Added {}. These are the coins I am watching:\n".format(coinTicker) + showAlertCoins(sheet_coin)
                            send_message(sender_id, botReply)

                        else:
                            botReply = "That coin is not included"
                            send_message(sender_id, botReply)



                    # delete coin
                    elif sliceWords(message_text, 0, -1).lower() in deleteTrigger:
                        refreshCMCData()
                        coinTickerList = getCoinTickerList(CMCdata)

                        if coinTicker in coinTickerList:
                            deleteCoinData(coinTicker, sheet_coin)
                            botReply = "deleted {}. These are the coins I am watching:\n".format(coinTicker) + showAlertCoins(sheet_coin)
                            send_message(sender_id, botReply)

                        else:
                            botReply = "That coin is not included"
                            send_message(sender_id, botReply)



                    # change percentage
                    elif sliceWords(message_text, 0, -1).lower() in changePercentageValueTrigger:
                        if isFloat(newPercentageValue):
                            setPercentageValue(newPercentageValue)
                            botReply = "The new percentage trigger to get an alert is now {}%".format(getPercentageValue())
                            send_message(sender_id, botReply)
                              
                        else:
                            botReply = 'This is not a valid value for the percentage. You do not have to write the "%" character.'
                            send_message(sender_id, botReply)



                    # update
                    elif message_text.lower() == 'update':
                        botReply = "Updated! I will be able to send again for the next 24 hours."
                        send_message(sender_id, botReply)



                    # help
                    elif message_text.lower() == 'help':
                        botReply = 'This bot will notify you when a coin pumps or drops below a certain percentage value.' \
                                    '\nThe bot can only send messages in a period of 24 hours later than when it recieved the last message from you. So in order to recieve messages everyday do not forget to press the "update" button once in a while. This bot will be sleeping from 23:00 until 7:00 Brussels time.' \
                                    '\n\n-You can add a coin to the watchlist by sending "add" and the ticker of that coin.' \
                                    '\n\n-You can delete a coin by typing "delete" and the ticker of that coin.' \
                                    '\n\n-You can show the coins the bot is watching by typing "show".' \
                                    '\n\n-You can change the value of the percentage by typing "change" or "change percentage to" and the value you want it to have. For example "change percentage to 25".'
                        send_message(sender_id, botReply)



                    # test message
                    elif message_text.lower() == "test message":
                        for user in getUserList():
                            botReply = "test"
                            send_message(user, botReply)



                    # add user
                    elif sliceWords(message_text, 0, -1).lower() == "add user":
                        addUser(userID)
                        botReply = "Added a new user."
                        send_message(sender_id, botReply)
                        print(getUserList())
                        
                        
                           
                    # delete user
                    elif sliceWords(message_text, 0, -1).lower() == "delete user":
                        deleteUser(userID)
                        botReply = "Deleted a user."
                        send_message(sender_id, botReply)
                        print(getUserList())


                           
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
