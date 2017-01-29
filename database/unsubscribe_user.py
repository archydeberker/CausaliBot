# First point of contact after a user has requested unsubscribe.

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
import db_utils as db

email = sys.argv[1]
print("Removing outstanding trials for user %s" % email)

db.unsubscribe_user(email=email)

print("Finished unsubscribe_user.py")