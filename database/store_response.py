# First point of contact after a user has signed up for the meditation experiment.

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
import db_utils as db

trialHash = sys.argv[1]
try:
	rating = int(sys.argv[2])
except ValueError:
	rating = -99999

print("trialHash: %s. Rating: %d" % (trialHash, rating))

db.store_response(trialHash, rating)

print("Finished store_response.py")