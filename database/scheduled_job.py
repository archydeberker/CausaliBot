#!/usr/bin/python

"""This script is ran on a regular basis to do basic housekeeping.

"""
print("Running scheduled_job.py")
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
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


# Do verification
# when the endpoint is registered as a webhook, it must echo back
# the 'hub.challenge' value it receives in the query arguments

def verify():
	if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
	    if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
	        return "Verification token mismatch", 403
	    return request.args["hub.challenge"], 200

	return "Hello world", 200

# Now send stuff
db_utils.fb_send_outstanding_instructions()
db_utils.fb_send_outstanding_response_prompts()
#db_utils.update_results() # Archy 250217: I can't find this function
print("Total number of completed trials in collection: %d" % (db_utils.trials_completed()))
