"""Python script to try out functionality in db_utils.py.

Run it from the zapscience parent directory using
python -m database.debug.py

Should run this on a local database so you can just delete the entire database when you're done. 
"""

import db_utils as db
from bson.objectid import ObjectId
import datetime
_, _, trials_coll = db.open_connection(collectionName='trials')

user = db.store_user('test', 'test@test.com')
user_id = user.inserted_id
print("user: %s" % user_id)
exp = db.init_experiment_meditation()
exp_id = exp.inserted_id
print("Experiment: %s" % exp_id)
foo = db.insert_trials(user_id, exp_id)
trial_ids = [str(foo.inserted_id) for foo in trials]
print("Inserted trials: %d" % len(trials))
print("updating a trial to have a response date in the past")
trials_coll.update_one({"_id": ObjectId(trial_ids[0])}, {'$set': {'response_date': datetime.datetime.utcnow()}})





result = db.init_results(str(user_id), str(exp_id))
result_id = result.inserted_id
print("Result id: %s" % result_id)
# complete a few trials

# store_response wants a hash, so find it in the trials_coll
db.store_response(trials_coll.find_one({'_id': trials[0].inserted_id})['hash_sha256'], 2)
db.store_response(trials_coll.find_one({'_id': trials[1].inserted_id})['hash_sha256'], 1)
db.store_response(trials_coll.find_one({'_id': trials[3].inserted_id})['hash_sha256'], 4)
db.store_response(trials_coll.find_one({'_id': trials[4].inserted_id})['hash_sha256'], 3)
db.store_response(trials_coll.find_one({'_id': trials[5].inserted_id})['hash_sha256'], 1)
db.store_response(trials_coll.find_one({'_id': trials[7].inserted_id})['hash_sha256'], 3)
db.store_response(trials_coll.find_one({'_id': trials[8].inserted_id})['hash_sha256'], 2)
db.store_response(trials_coll.find_one({'_id': trials[11].inserted_id})['hash_sha256'], 3)
db.store_response(trials_coll.find_one({'_id': trials[13].inserted_id})['hash_sha256'], 4)
db.store_response(trials_coll.find_one({'_id': trials[15].inserted_id})['hash_sha256'], 4) 

# calculate results
db.update_results()


raw_input("Press ENTER to finish debugging and delete all tmp data...")
# clean up. Notvery useful as probably the code crashed prior to this 
# given you're debugging
db.delete_user(str(user_id))
db.delete_experiment(str(exp_id))
db.delete_trials(trial_ids)
db.delete_result(result_id)