import os
import sys
import json
import urllib2
import re
from database import db_utils
from database import wit
from database import msg
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
                    print("PRINTING THE USER INFO")
                    print(txt_dict)
                    
                    # Check whether sender is in the database.
                    new_user = db_utils.fb_check_new_user(sender_id)

                    if new_user:
                        print("NEW USER! WOOHOO!")
                        send_message(sender_id, msg.rnd('greeting') + ' ' + txt_dict['first_name'] + ', nice to meet you! Welcome to Causali!')
                        send_image(sender_id)
                        send_message(sender_id, 'Type "start experiment" to get started, or "help" for all commands.')
                        # store the user in the DB
                        db_utils.fb_store_user(txt_dict['first_name'], txt_dict['last_name'], sender_id, txt_dict['timezone'])
                    else:  # if returning user
                        exp_state = db_utils.fb_user_check_experiment_signup_status(sender_id)
                        print(exp_state)

                        ####### EXPLICIT COMMANDS
                        if message_text.lower() == 'start experiment':
                            if exp_state != "no experiment":
                                send_message(sender_id, "Another one? You already have an experiment registered with us...")
                                if exp_state == 'complete':
                                    send_message(sender_id, "You can just wait for your next instruction.")
                                else:
                                    send_message(sender_id, "Let's complete your setup for that.")
                                    get_next_info(sender_id, message_text)
                            else:
                                send_message(sender_id, "Chocks away!")
                                db_utils.fb_init_experiment_meditation(sender_id)
                                send_message(sender_id, "What time would you like your meditation prompt email?")
                        elif message_text.lower() == 'help':
                            send_message(sender_id, 
                            """Try any of these:
start experiment
delete experiment
delete user
                            """
                            )
                        elif message_text.lower() == 'delete experiment':
                            r = db_utils.fb_delete_experiment(sender_id)
                            if r.deleted_count == 0:
                                send_message(sender_id, "You have no experiments. Try 'start experiment'")
                            else:
                                send_message(sender_id, str(r.deleted_count) + " experiments deleted.")
                                send_message(sender_id, "Science has left the building :(")
                        elif message_text.lower() == "delete user":
                            db_utils.fb_delete_experiment(sender_id)
                            r = db_utils.fb_delete_user(sender_id)
                            send_message(sender_id, "Why you go? Your experiments and user details been removed :(")

                        # The next ones test against state of the experiment, so all explicit commands need to go above this line
                        elif exp_state in ['instructionTime','responseTime']:
                            get_next_info(sender_id, message_text)
                        elif exp_state == 'no experiment':  # if user doesn't have experiment but didn't say one of the commands, then God knows what they want
                            send_message(sender_id, "You're not making yourself clear. Unless you say \"start experiment\", I'll have no clue what you're saying. Or try \"help\"")
                        elif exp_state == 'complete':  # if they already have complete experiment
                            send_message(sender_id, "You're already set for the experiment. Try \"help\" if you're really stuck.")
                            

                    

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):
    '''Send plain text message to recipient through facebook.

    Documentation: https://developers.facebook.com/docs/messenger-platform/send-api-reference/text-message

    '''

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


def send_image(recipient_id, image_url=msg.rnd_gif(tag='science')):
    """ Sends an image at the location of the image_url. 

    Facebook docs: https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment

    If none given, sends a random giphy gif
    """
    log("sending IMAGE to {recipient}: {text}".format(recipient=recipient_id, text=image_url))

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
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url
                }
            }
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
    action=db_utils.fb_user_check_experiment_signup_status(sender_id)
    log(action)

    if action=='instructionTime': # need to get first timepoint
    # TO DO: currently, after it has sucessfully returned a 'gotcha' message for meditation time, it still returns flag 'instructionTime' on next msg...
    # Don't know whether this is problem with entering into or checking the database.

        # Try and get timepoint from current message
        timepoint = format_timepoint(message_text)
        print('Time parsed:', timepoint)
        if timepoint is not None:
            send_message(sender_id, "Gotcha, "+str(timepoint))
            db_utils.fb_update_experiment(sender_id, 'instructionTimeLocal', timepoint)
            send_message(sender_id,"And what time would you like me to ask how you're feeling?")
        else:
            send_message(sender_id, "Sorry, I didn't quite understand that.")
            send_message(sender_id, "What time would you like your meditation prompt email?")

    elif action=='responseTime':
        timepoint = format_timepoint(message_text)
        print('Time parsed:', timepoint)
        if timepoint is not None:
            send_message(sender_id, "Aye aye, captain, we'll be sailing at "+str(timepoint))
            db_utils.fb_update_experiment(sender_id, 'responseTimeLocal', timepoint)
            send_message(sender_id,"We've got everything we need for take-off, so hold on to your gonads!")
   
        else:
            send_message(sender_id, "Sorry, I didn't quite understand that.")
            send_message(sender_id,"What time would you like me to ask how you're feeling?")


def format_timepoint(message_text):
    ''' Return formatted time string based upon message text e.g. '7am'.
    Does so via a call to the Wit.ai interface.

    inputs:     message_text (str)
    '''   

    msg_dict = wit.understand_string(message_text)
    log(msg_dict)
    
    # check if the correct values are returned by 
    if 'datetime' in msg_dict['entities']:
        log('found datetime')
        if 'values' in msg_dict['entities']['datetime'][0]:
            log('found values')
            if 'value' in msg_dict['entities']['datetime'][0]['values']:  # could not contain value if it detects e.g. a time range.
                log('found value') 
                return wit.timestamp_to_simple_string(msg_dict)
    # value not found, return None
    else:
        return None


if __name__ == '__main__':
    app.run(debug=True)
