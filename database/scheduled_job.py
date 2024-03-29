#!/usr/bin/python

"""This script is ran on a regular basis to do basic housekeeping.

"""
print("Running scheduled_job.py")
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
from database import db_utils
from database import wit
from database import msg
import requests
import datetime
from flask import Flask, request

# Now send stuff

db_utils.fb_send_outstanding_instructions()
db_utils.fb_send_outstanding_response_prompts()
