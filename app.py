import os
import sys
import json
import urllib2
import re
from database import db_utils
from database import wit
from database import msg
import requests
import datetime
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
    # log(data)  # you may not want to log every incoming message in production, but it's good for testing

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
                    # print("PRINTING THE USER INFO")
                    # print(txt_dict)
                    
                    # Check whether sender is in the database.
                    new_user = db_utils.fb_check_new_user(sender_id)

                    if new_user:
                        # print("NEW USER! WOOHOO!")
                        msg.send_plain_text(sender_id, msg.rnd_text_string('greeting') + ' ' + txt_dict['first_name'] + ', nice to meet you! Welcome to Causali!')
                        msg.send_image(sender_id)
                        msg.send_plain_text(sender_id, 'Type "start experiment" to get started, or "help" for all commands.')
                        msg.send_quick_reply_rating(
                            fb_id = sender_id, 
                            prompt = 'On a scale from 0 to 10, where 0 is miserable and 10 is as happy as you\'ve ever been, how happy do you feel right now?', 
                            question_identifier = 'intro_happiness_rating'
                            )
                        # store the user in the DB
                        db_utils.fb_store_user(
                            first_name=txt_dict['first_name'], 
                            second_name=txt_dict['last_name'], 
                            fb_id=sender_id, 
                            timezone_offset=txt_dict['timezone']
                            )
                    else:  # if returning user
                        # check if this is a response to a quick reply
                        if "quick_reply" in messaging_event["message"]:
                            # give the whole object, including sender id, message text, and quick replies
                            # Will also send the required messages back to user.
                            question, response = db_utils.parse_quick_reply(messaging_event)
                            ### Cycle through different responses
                            # generic logging for now. 

                            r = db_utils.fb_log_entry(sender_id, question, response)
                            if r.acknowledged:
                                msg.send_plain_text(sender_id, 'Thanks, we\'ve stored your response.')
                            else:
                                msg.send_plain_text(sender_id, 'Something went wrong, we didn\'t store your response =/')
                            

                        else:  # not a quick reply
                            exp_state = db_utils.fb_user_check_experiment_signup_status(sender_id)
                            # print(exp_state)

                            ####### EXPLICIT COMMANDS
                            if message_text.lower() == 'start experiment':
                                if exp_state != "no experiment":
                                    msg.send_plain_text(sender_id, "Another one? You already have an experiment registered with us...")
                                    if exp_state == 'complete':
                                        msg.send_plain_text(sender_id, "You can just wait for your next instruction.")
                                    else:
                                        msg.send_plain_text(sender_id, "Let's complete your setup for that.")
                                        get_next_info(sender_id, message_text)
                                else:
                                    msg.send_plain_text(sender_id, "Chocks away!")
                                    db_utils.fb_init_experiment_meditation(sender_id)
                                    msg.send_plain_text(sender_id, "What time would you like your meditation prompt email?")
                            elif message_text.lower() == 'help':
                                msg.send_plain_text(sender_id, 
                                """Try any of these:
    start experiment
    delete experiment
    delete user
    gif me science
                                """
                                )
                            elif message_text.lower() == 'delete experiment':
                                r = db_utils.fb_delete_experiment(sender_id)
                                if r.deleted_count == 0:
                                    msg.send_plain_text(sender_id, "You have no experiments. Try 'start experiment'")
                                else:
                                    msg.send_plain_text(sender_id, str(r.deleted_count) + " experiments deleted.")
                                    msg.send_plain_text(sender_id, "Science has left the building :(")
                            elif message_text.lower() == "delete user":
                                db_utils.fb_delete_experiment(sender_id)
                                db_utils.fb_delete_user(sender_id)  
                                db_utils.fb_delete_trials(sender_id)  # should probably only delete incomplete ones.
                                msg.send_plain_text(sender_id, "Why you go? Your experiments, trials, and user details been removed :(")
                            elif message_text.lower() == 'gif me science':
                                msg.send_image(sender_id)
                            elif 'log' in message_text.lower(): # flexible function for logging data
                                
                                err,log_name,log_value= parse_log_input(message_text.lower()) # parse message
                                if err==0:
                                    db_utils.fb_log_entry(sender_id, log_name, log_value) # store in database in generic user_logs table
                                    msg.send_plain_text(sender_id, "Successfully logged %s as %s. Come onnnn!!!!"%(log_name,log_value))
                                else:
                                    msg.send_plain_text(sender_id, "Hmmm. Please log like this: log 'something' 'value of something', such as 'log breakfast eggs'")
                            
                            ##### The next ones test against state of the experiment, so all explicit commands need to go above this line #####
                            elif exp_state in ['instructionTime','responseTime']:
                                get_next_info(sender_id, message_text)
                            elif exp_state == 'no experiment':  # if user doesn't have experiment but didn't say one of the commands, then God knows what they want
                                msg.send_plain_text(sender_id, "You're not making yourself clear. Unless you say \"start experiment\", I'll have no clue what you're saying. Or try \"help\"")
                            elif exp_state == 'complete':  # if they already have complete experiment
                                msg.send_plain_text(sender_id, "You're already set for the experiment. Try \"help\" if you're really stuck.")
                                

                    

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200





def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()

def parse_log_input(message):
    ''' This takes a message which contains the word 'log' and attempts to parse out the log name and value that the user wishes to insert.
    This is currently based on the assumption that the word after 'log' denotes the log name, and all the words after that are the things to be logged.
    Currently this process is rather type-agnostic: aren't doing any work to figure out strings vs. numbers etc. 

    # TO DO (11/2/17) : how to deal with multi-word lognames?'''

    # Convert message to list of words
    msg_list = re.sub("[^\w]", " ",  message).split() # here any non-alphanumeric characters are replaced by spaces

    # Get word after log, and the word after that
    try:
        log_name = msg_list[msg_list.index('log')+1]
        log_value = msg_list[msg_list.index('log')+2:]
        log_value = str(' '.join(log_value))  # take everything after the log name as input, format as single string (us str command to remove unicode marker)
        error_flag = 0 
    except:
        error_flag = 1
        log_name = ''
        log_value = ''

    # deal with special case where log_value is 'time', meaning user wants to log current time
    if log_value=='time':
        log_value = str(datetime.datetime.utcnow())

    return error_flag,log_name,log_value

def get_next_info(sender_id,message_text):
    ''' This looks up the state of the user in the database, and finishes collecting
    any data that's required

    Input:  sender_id (str) '''

    # Check database status, This will initiate the experiment if not already done so, and return a flag as to the next necessary argument
    action=db_utils.fb_user_check_experiment_signup_status(sender_id)
    # log(action)

    if action=='instructionTime': # need to get first timepoint
    # TO DO: currently, after it has sucessfully returned a 'gotcha' message for meditation time, it still returns flag 'instructionTime' on next msg...
    # Don't know whether this is problem with entering into or checking the database.

        # Try and get timepoint from current message
        timepoint = format_timepoint(message_text)
        # print('Time parsed:', timepoint)
        if timepoint is not None:
            msg.send_plain_text(sender_id, "Gotcha, "+str(timepoint))
            db_utils.fb_update_experiment(sender_id, 'instructionTimeLocal', timepoint)
            msg.send_plain_text(sender_id,"And what time would you like me to ask how you're feeling?")
        else:
            msg.send_plain_text(sender_id, "Sorry, I didn't quite understand that.")
            msg.send_plain_text(sender_id, "What time would you like your meditation prompt email?")

    elif action=='responseTime':
        timepoint = format_timepoint(message_text)
        # print('Time parsed:', timepoint)
        if timepoint is not None:
            msg.send_plain_text(sender_id, "Aye aye, captain, we'll be sailing at "+str(timepoint))
            db_utils.fb_update_experiment(sender_id, 'responseTimeLocal', timepoint)
            msg.send_plain_text(sender_id,"We've got everything we need for take-off, so hold on to your gonads!")
            # actually implement all the trials
            success = dbutils.fb_init_trials(sender_id)
            if success:
                msg.send_plain_text(sender_id,"We've lined up your experiment for execution. All you have to do is sit back and wait for further instructions!")
                msg.send_image(recipient_id, image_url=msg.rnd_gif(tag='relax chill'))
            else:
                msg.send_plain_text(sender_id,"Something's gone horribly wrong, and your experiment may or may not have survived. An admin will be in touch.")
   
        else:
            msg.send_plain_text(sender_id, "Sorry, I didn't quite understand that.")
            msg.send_plain_text(sender_id,"What time would you like me to ask how you're feeling?")


def format_timepoint(message_text):
    ''' Return formatted time string based upon message text e.g. '7am'.
    Does so via a call to the Wit.ai interface.

    inputs:     message_text (str)
    '''   

    msg_dict = wit.understand_string(message_text)
    log(msg_dict)
    
    # check if the correct values are returned by 
    if 'datetime' in msg_dict['entities']:
        # log('found datetime')
        if 'values' in msg_dict['entities']['datetime'][0]:
            # log('found values')
            if 'value' in msg_dict['entities']['datetime'][0]['values'][0]:  # could not contain value if it detects e.g. a time range.
                # log('found value') 
                return wit.timestamp_to_simple_string(msg_dict)
    # value not found, return None
    else:
        return None


if __name__ == '__main__':
    app.run(debug=True)
