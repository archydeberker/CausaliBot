import os
import sys
import json
import urllib2
from database import db_utils
from datetime import strptime

import requests
from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])

def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    # Get the user's ID
                    txt = urllib2.urlopen("https://graph.facebook.com/v2.6/"+sender_id+"?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token="+os.environ["PAGE_ACCESS_TOKEN"]).read()
                    txt_dict = json.loads(txt)
                    
                    # Check whether sender is in the database. If not, add them.
                    new_user = db_utils.fb_check_new_user(sender_id)

                    if new_user:
                        send_message(sender_id,'Hey ' + txt_dict['first_name'] + ' nice to meet you! Welcome to Causali!')
                        db_utils.fb_store_user(txt_dict['first_name'],txt_dict['second_name'],sender_id,txt_dict['timezone'])
                        send_message(sender_id,"To setup your first experiment, type start experiment")
                    else:
                        get_next_info(sender_id,message_text)

                    # Continue with gathering information as necessary
                    

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
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
    print str(message)
    sys.stdout.flush()

def get_next_info(sender_id,message_text):
    ''' This looks up the state of the user in the database, and finishes collecting
    any data that's required

    Input:  sender_id (str) '''

    # Check database status, This will initiate the experiment if not already done so, and return a flag as to the next necessary argument
    action=db_utils.fb_check_experiment_setup(sender_id)

    if action=='instructionTime': # need to get first timepoint
        # Try and get timepoint from current message
        try:
            timepoint = format_timepoint(message_text)
            print(timepoint)
            fb_update_experiment_meditation(sender_id, 'instructionTime', timepoint)
        except:
            send_message(sender_id,"What time would you like your mediation prompt email? Enter a time in a 12 hour format along with AM or PM.")
    elif action=='responseTime':
        # Try and get timepoint from current message
        try:
            timepoint = format_timepoint(message_text)
            print(timepoint)
            fb_update_experiment_meditation(sender_id, 'instructionTime', timepoint)
        except:
            send_message(sender_id,"What time would you like your mediation prompt email? Enter a time in a 12 hour format along with AM or PM.")
        


def format_timepoint(message_text):
    ''' Return formatted time string based upon message text e.g. '7am'.
    Does so via a call to the Wit.ai interface.

    inputs:     message_text (str)'''   

    rq = urllib2.Request('https://api.wit.ai/message?v=20170129&q='+message_text,headers={"Authorization": "Bearer FS4CJQVZGWFNJ525V5JJ7NVR5SWBDUIG"})
    msg = urllib2.urlopen(rq).read()

    msg_dict = json.loads(msg)
    timepoint = msg_dict['datetime']['values']

    return timepoint


if __name__ == '__main__':
    app.run(debug=True)
