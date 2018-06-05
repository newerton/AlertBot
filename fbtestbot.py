from flask import Flask, request
import requests
import sys
import os
import json
from Credentials import *
import time
import datetime
import _thread
import urllib.request
app = Flask(__name__)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
import playerPortfolioValues


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
sheet_simulation = client.open('crypto simulation').sheet1
sheet_simulation_trigger = client.open('simulation_trigger').sheet1

# --------------------------------------------------------------------------------------------------------------------------
#                                                               simulation
# --------------------------------------------------------------------------------------------------------------------------

# --------------------
# get global data
# --------------------
CMC_global_URL = "https://api.coinmarketcap.com/v2/global/"
with urllib.request.urlopen(CMC_global_URL) as cmc_global_url:
    read_global = cmc_global_url.read()
CMC_global_data = json.loads(read_global)


def refresh_global_data():
    with urllib.request.urlopen(CMC_global_URL) as cmc_global_url:
        global read_global, CMC_global_data
        read_global = cmc_global_url.read()
    CMC_global_data = json.loads(read_global)


# -------------------
# refresh credentials
# --------------------
def visible_sleeper(seconds):
    for timer in range(seconds):
        time.sleep(1)
        if timer % 10 == 0:
            print("timer is at {}".format(timer))


def refreshCredentialsForSimulation():
    refreshTime = 100

    global scope, creds, client
    global sheet_simulation

    print("Refreshing credentials for simulation...")
    scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    sheet_simulation_trigger = client.open('simulation_trigger').sheet1
    
    visible_sleeper(refreshTime)
    print("Refreshed credentials for simulation.")

def refreshCredentialsForSimulationTrigger():
    global scope, creds, client
    global sheet_simulation_trigger

    print("Refreshing credentials for trigger...")
    scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    sheet_simulation_trigger = client.open('simulation_trigger').sheet1
    print("Refreshed credentials for trigger.")


# ------------
# trigger defs
# ------------
def set_trigger_value(value):
    refreshCredentialsForSimulationTrigger()
    sheet_simulation_trigger.update_cell(1, 1, value)


def get_trigger_value():
    refreshCredentialsForSimulationTrigger()
    value = int(sheet_simulation_trigger.col_values(1)[0])
    return value


# ------------------
# set up spreadsheet
# ------------------
def write_player_number():
    number_of_players = 1000

    for player_number in range(number_of_players):
        if player_number % 95 == 0:
            refreshCredentialsForSimulation()
        sheet_simulation.update_cell(player_number + 2, 1, "player {}".format(player_number + 1))


# -------------------
# create cryptofolios
# -------------------
def getCoinPrice(ticker):
    coin_info = next(coin for coin in CMCData if coin[u'symbol'] == ticker)

    return (coin_info[u'price_usd'])


def getCoinList(dataList):
    coinList = []

    for coinDetails in dataList:
        coinName = coinDetails[u'symbol']
        coinList += [coinName]

    return coinList


def choosePortfolio(coinList):
    beginPortfolioValue = 1000
    remainingValue = beginPortfolioValue
    counter = 0
    portfolioList = []

    while remainingValue > 0:
        coin = coinList[random.randint(0, 99)]
        amountOfUSD = random.randint(0, 300)

        if counter == 4:
            amountOfUSD = remainingValue

        elif remainingValue - amountOfUSD < 0:
            amountOfUSD = remainingValue

        amountOfCoins = round(amountOfUSD / float(getCoinPrice(coin)), 4)
        remainingValue -= amountOfUSD
        counter += 1
        portfolioList += [[coin, amountOfCoins]]

    return portfolioList


def createPlayerList(coinList):
    listOfPlayers = []

    for player in range(1000):
        playerDictionary = {}
        playerDictionary['portfolio'] = choosePortfolio(coinList)
        listOfPlayers += [playerDictionary]

    return listOfPlayers


# --------------------------------
# get value of created portfolios
# --------------------------------
def getPlayerPortfolioValue(portfolio):
    portfolioValue = 0

    try:
        for portfolioElement in portfolio:
            ticker = portfolioElement[0]
            coinValue = float(getCoinPrice(ticker))
            amountOfCoins = portfolioElement[1]
            elementValue = amountOfCoins * coinValue
            portfolioValue += elementValue
        return round(portfolioValue, 2)

    except:
        return "ERROR"


def createPlayerPortfolioValueList(playerList):
    playerPortfolioValueList = []

    for player in playerList:
        playerPortfolio = player['portfolio']
        playerPortfolioValue = getPlayerPortfolioValue(playerPortfolio)
        playerPortfolioValueList += [playerPortfolioValue]

    return playerPortfolioValueList


# ----------------------------------
# get total market cap and write it
# ----------------------------------
def get_total_market_cap():
    refresh_global_data()
    total_market_cap = CMC_global_data["data"]["quotes"]["USD"]["total_market_cap"]
    return str(total_market_cap)


def isFloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def makeLargeNumberReadable(originalstring):
    if isFloat(originalstring):
        intstring = str(int(float(originalstring) + 0.5))
        intstringlist = list(intstring)
        firstcommaindex = len(intstring) % 3
        amountofcommas = (len(intstring) // 3)

        if firstcommaindex == 0:
            amountofcommas -= 1

        for commaindex in range(amountofcommas):
            intstringlist.insert((-3 * (commaindex + 1)) - commaindex, ',')

        newstring = ''.join(intstringlist)
        return newstring

    else:
        return "Error converting large number to readable number."


def write_total_market_cap(col):
    total_market_cap = makeLargeNumberReadable(get_total_market_cap())
    sheet_simulation.update_cell(1013, col, total_market_cap)
         

# ------------------------
# get average, max and min
# ------------------------
def get_maximum_value(portfolio_value_list):
    list_without_errors = []
    for value in portfolio_value_list:
        if value != "ERROR":
            list_without_errors += [value]

    maximum = max(list_without_errors)

    for index in range(len(portfolio_value_list)):
        if portfolio_value_list[index] == maximum:
            maxIndex = index
            break

    return [maximum, maxIndex]


def get_minimum_value(portfolio_value_list):
    list_without_errors = []
    for value in portfolio_value_list:
        if value != "ERROR":
            list_without_errors += [value]

    minimum = min(list_without_errors)

    for index in range(len(portfolio_value_list)):
        if portfolio_value_list[index] == minimum:
            minIndex = index
            break

    return [minimum, minIndex]


def get_average_value(portfolio_value_list):

    list_without_errors = []
    for value in portfolio_value_list:
        if value != "ERROR":
            list_without_errors += [value]

    sum_of_values = 0
    for new_values in list_without_errors:
        sum_of_values += new_values

    average = sum_of_values / len(list_without_errors)

    return round(average, 2)


# ----
# date
# ----
def get_date_string():
    now = datetime.datetime.now()
    date = "{}/{}/{}".format(now.day, now.month, now.year)
    return date


def write_date(column):
    sheet_simulation.update_cell(1, column, get_date_string())


def get_utc_day_name():
    now = datetime.datetime.utcnow()
    day_name = now.strftime('%A')
    return day_name


# ---------------------------
# write values in spreadsheet
# ---------------------------
def write_portfolios(portfolio_list, column):
    counter = 1

    for portfolio in portfolio_list:
        if counter % 90 == 0:
            refreshCredentialsForSimulation()

        sheet_simulation.update_cell(counter + 1, column, "{}".format(portfolio['portfolio']))
        counter += 1


def write_portfolio_values(portfolio_value_list, column):
    counter = 1

    for value in portfolio_value_list:
        if counter % 90 == 0:
            print("currently at portfolio {}".format(counter + 1))
            refreshCredentialsForSimulation()

        sheet_simulation.update_cell(counter + 1, column, "{}".format(value))
        counter += 1


def write_details(column, value_list, player_list):
    write_date(column)

    average = get_average_value(value_list)
    sheet_simulation.update_cell(1005, column, average)

    max = get_maximum_value(value_list)[0]
    max_portfolio_index = get_maximum_value(value_list)[1]
    max_portfolio = str(player_list[max_portfolio_index]['portfolio'])
    sheet_simulation.update_cell(1007, column, max)
    sheet_simulation.update_cell(1008, column, max_portfolio)

    min = get_minimum_value(value_list)[0]
    min_portfolio_index = get_minimum_value(value_list)[1]
    min_portfolio = str(player_list[min_portfolio_index]['portfolio'])
    sheet_simulation.update_cell(1010, column, min)
    sheet_simulation.update_cell(1011, column, min_portfolio)


def get_nb_rows(sheet):
    nb_rows = len(sheet.get_all_records()) + 1
    return nb_rows


def get_nb_cols(sheet):
    nb_cols = len(sheet.get_all_records()[1])
    return nb_cols


def simulation():
    refreshCredentialsForSimulation()
    column = get_nb_cols(sheet_simulation) + 1
    player_list = playerPortfolioValues.player_portfolios
    value_list = createPlayerPortfolioValueList(player_list)

    write_total_market_cap(column)                                            
    write_details(column, value_list, player_list)
    write_portfolio_values(value_list, column)


def main_simulation_thread():
    while True:
        trigger_value = get_trigger_value()
        day_name = get_utc_day_name()

        if trigger_value == 1 and day_name == 'Wednesday':
            print('starting simulation.')
            simulation()
            set_trigger_value(0)

        elif day_name == 'Thursday' and trigger_value == 0:
            set_trigger_value(1)

        else:
            print("No simulation triggered. Simulation thread is going to sleep ...")
            time.sleep(60 * 60 * 2)

         
# ----------------------------------------------------------------------------------------------------------------------------
#                                                     NEX allocation start
# ----------------------------------------------------------------------------------------------------------------------------

# -------------
# get cmc data
# -------------
def get_cmc_data():
    try:
        url = "https://api.coinmarketcap.com/v1/ticker/?limit=1400"
        url_open = urllib.request.urlopen(url)
        url_read = url_open.read()
        data = json.loads(url_read)
        return data

    except:
        print("An error occurred")
        return None


def get_price(ticker, data):
    for coin_data in data:
        if coin_data["symbol"] == ticker:
            return coin_data["price_usd"]
    return False


# --------------------------
# set up Google spreadsheets
# --------------------------
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(credentials)
work_sheet = client.open("NEX allocation").sheet1


def replace_comma_with_dot(string):
    return "".join([letter if letter != "," else "." for letter in string])


def convert_string_to_float(string):
    print("to convert ", string)
    string = replace_comma_with_dot(str(string))
    return float(string)


def nex_main():
    print("start")
    data = get_cmc_data()
    dictionary_list = work_sheet.get_all_records()

    if dictionary_list[-1]["coin name"] == "Total":
        work_sheet.delete_row(len(dictionary_list) + 1)
        dictionary_list = work_sheet.get_all_records()

    gspread_nb_rows = len(dictionary_list) + 1
    total_funds = 0

    for index in range(len(dictionary_list)):
        print(index)
        gspread_row = index + 2
        dictionary = dictionary_list[index]
        ticker = dictionary["coin name"]
        price_per_coin = convert_string_to_float(get_price(ticker, data))
        amount_of_coins = convert_string_to_float(dictionary["amount"])
        coin_funds = round(price_per_coin * amount_of_coins, 2)

        work_sheet.update_cell(gspread_row, 3, price_per_coin)
        work_sheet.update_cell(gspread_row, 4, coin_funds)

        total_funds += coin_funds

    print("escaped out of loop")
    work_sheet.update_cell(gspread_nb_rows + 1, 1, "Total")
    work_sheet.update_cell(gspread_nb_rows + 1, 4, round(total_funds, 2))
    bot_reply = "total funds are: ${}".format(round(total_funds, 2))
    print("done")
    return bot_reply


# ----------------------------------------------------------------------------------------------------------------------------
#                                                     Alert Bot
# ----------------------------------------------------------------------------------------------------------------------------

# ----
# vars
# ----
refreshRateMinutes = 2
refreshRateSeconds = 60 * refreshRateMinutes

addTrigger = ["add"]
deleteTrigger = ["del", "delete"]
showTrigger = ["show", "show list"]
changePercentageValueTrigger = ["change", "change percentage", "change percentage to"]

CMC_URL = "https://api.coinmarketcap.com/v1/ticker/?limit=1400"
with urllib.request.urlopen(CMC_URL) as cmc_url:
    s = cmc_url.read()
CMCData = json.loads(s)

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



coinTickerList = getCoinTickerList(CMCData)



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
    return float(getCoinInfoElement(ticker, 'percent_change_1h', CMCData))



def getUsdPrice(ticker):
    return float(getCoinInfoElement(ticker, 'price_usd', CMCData))



def getBtcPrice(ticker):
    return float(getCoinInfoElement(ticker, 'price_btc', CMCData))



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
                usd_price = getUsdPrice(coin_ticker)
                btc_price = getBtcPrice(coin_ticker)
                bot_reply = "{} changed {}% in the last hour. The price of {} is now ${} or {} BTC.".format(coin_ticker, one_hour_change, coin_ticker, usd_price, btc_price)
         
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

         
def refreshCredentials():
    refreshTime = 60 * 10.5

    global scope, creds, client
    global sheet_coin, sheet_FBIDs, sheet_percentage

    while True:
        print("Refreshing credentials ...")
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
        client = gspread.authorize(creds)

        sheet_coin = client.open('coins').sheet1
        sheet_FBIDs = client.open('FB IDs').sheet1
        sheet_percentage = client.open('percentage').sheet1
        print("Refreshed credentials.")
        time.sleep(refreshTime)


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
                        coinTickerList = getCoinTickerList(CMCData)

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
                        coinTickerList = getCoinTickerList(CMCData)

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
                           
                           
                           
                    # nex                      
                    elif message_text.lower() == "nex":
                        botReply = nex_main()
                        send_message(sender_id, botReply
                        
                           
                                     
                    # delete user
                    elif sliceWords(message_text, 0, -1).lower() == "delete user":
                        deleteUser(userID)
                        botReply = "Deleted a user."
                        send_message(sender_id, botReply)
                        print(getUserList())

                           
                           
                    #simulation test
                    elif message_text.lower() == 'simulation test 4832':
                        botReply = "Starting a simulation test."
                        send_message(sender_id, botReply)
#                         simulation()
                        botReply = "Ended simulation."
                        send_message(sender_id, botReply)
                           
                           
                           
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
    error=True

    while error:
         try:
             print("starting threads")
             _thread.start_new_thread(threadOne, ())
             _thread.start_new_thread(main_simulation_thread, ())
             _thread.start_new_thread(refreshCredentials, ())
             _thread.start_new_thread(app.run(host='0.0.0.0', port=port), ())
             error=False
         except:
             print("Restarting function in 20 seconds due to error.")
             time.sleep(20)
             print("Restarting function...")
             error=True
