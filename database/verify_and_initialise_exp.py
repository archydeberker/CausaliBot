# First point of contact after a user has signed up for the meditation experiment.

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
import db_utils as db
from mail.email_defs import confirm_signup_meditation
from bson.objectid import ObjectId # to be able to query _id in mongo


email = sys.argv[1]
user_id = ObjectId(sys.argv[2])
exp_id = ObjectId(sys.argv[3])

# initialise trials
trials = db.init_trials(str(user_id), str(exp_id))
trial_ids = [str(foo.inserted_id) for foo in trials]
print("Inserted trials. First trial id: %s" % trial_ids[0])

# send an email to the user 
confirm_signup_meditation(email)


print("Finished verify_and_initialise_exp.py")