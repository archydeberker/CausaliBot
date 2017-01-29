# Get all results for a given user and return as a json object

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
import db_utils as db
import pymongo
from bson.objectid import ObjectId # to be able to query _id in mongo
from mail.email_defs import confirm_signup_meditation

experiment_id = sys.argv[1]
user_id = sys.argv[2]


print db.get_results(ObjectId(experiment_id),ObjectId(user_id))
