from flask import Flask, request
import requests
import sys
import os
import json
from Credentials import *
import time
import _thread

app = Flask(__name__)


@app.route('/', methods=['GET'])
def handle_verification():
    if request.args.get('hub.verify_token', '') == VERIFY_TOKEN:
        return request.args.get('hub.challenge', 200)
    else:
        return 'Error, wrong validation token'


@app.route('/', methods=['POST'])
def handle_messages():
    data = request.get_json()
    log(data)

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = "{}".format(sender_id)
                    
                    send_message(sender_id, message_text)
              

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
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
    log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()

    
def test():
    counter = 1

    while counter < 6:
        print(counter)
        time.sleep(15)
        counter += 1

        if counter == 5:
            send_message('1671872586244465', 'hello')
            print("done")
            counter = 1

            
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    try:
        _thread.start_new_thread(test, ())
        _thread.start_new_thread(app.run(host='0.0.0.0', port=port), ())
    
    except:
        print ("Error: unable to start thread")

    while 1:
        pass
