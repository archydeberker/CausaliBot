# set of functions to interact with the Wit AI

import json
import urllib
import requests


def understand_string(message_text):
    # send a string to wit and get structured info back.
    # For list of headers see https://www.cs.tut.fi/~jkorpela/http.html
    # Returns a dictionary if the call was successful.

    # make sure the message_text is allowed to have spaces
    query = {'q': message_text}
    headers = {"Authorization": "Bearer FS4CJQVZGWFNJ525V5JJ7NVR5SWBDUIG",
               'Content-Type': 'text/plain'}
    r = requests.get('https://api.wit.ai/message?', params=query, headers=headers)

    if r.status_code == 200:  # means success
        return r.json()

    else:
        print('Request to Wit failed for message:', message_text)
        print('Status code:', r.status_code)  # print the code
        return {}

def timestamp_to_simple_string(wit_object):
    """ Takes a with object that has detected a dateimeand makes it into a simple string that Causali code can understand

    Example input: "2017-01-30T07:00:00.000-08:00"
    """
    t = wit_object['entities']['datetime'][0]['values'][0]['value']
    return t[11:16]  # ugly, but parsing datetime strings is also fraught with shit.

