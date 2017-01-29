# First point of contact after a user has signed up for the meditation experiment.
# Will register the user and experiment, but not the trials. this happens after user has confirmed their email. 

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
import db_utils as db
from mail.email_defs import verify_user_by_email 

name = sys.argv[1]
email = sys.argv[2]
instructionTime = sys.argv[3]
responseTime = sys.argv[4]
timezone = sys.argv[5]

print(name, email)

# store the user
user = db.store_user(name, email, timezone)
user_id = user.inserted_id
print("Inserted user: %s" % user_id)

# initalise a new version of the experiment. Not ideal but works for now. (should just have one instance of the experiment which everyone signs up to, but I'm not sure how to hardcode that experiment in reliably.)
exp = db.init_experiment_meditation(user_id, instructionTime, responseTime)
exp_id = exp.inserted_id
print("Inserted experiment: %s" % exp_id)

####### AT THIS STAGE THE TRIALS HAVE NOT BEEN INITIATED. This will happen once the user is confirmed

# send a verification email to register the user
verify_user_by_email(email, user_id, exp_id, name)


print("Finished signup_meditation.py")