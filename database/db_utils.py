	# import packages
import sys
import os
# this adds the zapscience folder so we dont have to deal with bs relative path issues
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
sys.path.append('/app/frontend_play/dist/google-visualization-python-master')
import pymongo
import datetime
from bson.objectid import ObjectId # to be able to query _id in mongo
import numpy as np
import hashlib
import pandas as pd
from itertools import groupby
import pytz




# find the database URI. If not available in the environment, use local mongodb host
URI = os.getenv('MONGO_URI', 'mongodb://localhost')
# get the name of the database: either causali or causali-staging (or localhost).
db = URI.split('/')[-1]

# function definitions that can be used by other scripts
def open_connection(collectionName, URI=URI, db=db):
	""" Opens connection and returns connection details
	Inputs
		URI 			server to connect to (includes credentials)
		db 				database to connect to
		collectionName	what collection to set up
	Returns
		client 			handle to server
		db_handle 		handle to database
		coll_handle 	handle to collection (e.g. can now do coll.find({}))

	Example
		client, db, collection = open_connection(collectionName='users')
	"""
	client = pymongo.MongoClient(URI)
	db_handle = client[db]
	coll_handle = db_handle[collectionName]
	return client, db_handle, coll_handle


def close_connection(client):
	"""Close a connection
	Input:
		client 		class is pymongo.MongoClient() as generated by open_connection()
	"""
	client.close()


def init_trials(fb_id, experiment_id):
	""" Initialises all the trials for an experiment for a user, reading a document in the 'experiments' database and populating the 'trials' collection.

	This assumes that the experiment already exists in the database, and simply reads out the experiments and makes sure all reminders are set, timezones are corrected for,
	and order of conditions is randomised
	Inputs
		fb_id 		string, FACEBOOK id
		experiment_id 	string, not an ObjectId

	Returns
		input_result	array of insert results
	"""
	# get a handle to the users collection and experiments collection
	client, db_handle, users_coll = open_connection(collectionName='users')
	experiments_coll = db_handle['experiments']
	# get information about the experiment and store it into the variable
	exp = experiments_coll.find_one({"_id": ObjectId(experiment_id)})
	# get information about the user and store it into variable using next()
	user = users_coll.find_one({"fb_id": fb_id})
	
	# create an array of all the condition strings
	condition_array = []
	for ix, con in enumerate(exp["conditions"]): # iterate over each condition in the experiment
		# append the condition with appropriate number of replications
		condition_array += ([con] * exp["nTrials"][ix])
	# shuffle the array depending on requested method, either 1000 times or until satisfied. Wouldn't want to crash the server
	satisfied = False
	iterations = 0
	while (not satisfied) and (iterations<1000):
		# increase iterations 
		iterations += 1
		# select randomisation method
		if exp["randomise"] == 'complete':
			# completely random, no restraints on ordering
			np.random.shuffle(condition_array)
			satisfied = True
		elif exp["randomise"] == 'max3':	
			# shuffle in some way that maximally 3 times in a row the same condition is given
			np.random.shuffle(condition_array)
			# check if restraint is satisfied
			# https://stackoverflow.com/questions/29081226/limit-the-number-of-repeats-in-pseudo-random-python-list
			if all(len(list(group)) <= 3 for _, group in groupby(condition_array)):
				satisfied = True
	if not satisfied:
		print('did not reach criterion for randomising; using current state of condition_array instead')
	
	# make a pytz object to localise the dates and times. Some crucial notes on timezones:
	# - Once a date-aware object is written to Mongo it will be transformed to UTC. 
	# - create a timezone object using pytz.timezone('string')
	# - Transform an existing tz-aware datetime to another timezone using .astimezone(tz_object)
	tzUser = pytz.timezone(user['timezone'])
	tzUTC = pytz.utc
	# get current datetime in user's timezone
	nowLocal = tzUTC.localize(datetime.datetime.utcnow()).astimezone(tzUser)
	# get today's date so we know when 'tomorrow' is for this user. 
	dateLocal = nowLocal.date()
	tomorrowLocal = dateLocal + datetime.timedelta(days=1)
	# get the first condition email and response request in the user's local time, and localise it so that when it's 
	# STORED IN MONGO IT'S SET TO UTC AUTOMATICALLY. After that we can then just add 24 hours to each of these
	first_instruction_datetime = tzUser.localize(
		datetime.datetime.combine(  # combine tomorrow's date with the time to send the message
			tomorrowLocal, # tomorrow's date in user's tz
			datetime.datetime.strptime(exp["instructionTimeLocal"], '%H:%M').time()  # the time of day to send the prompt datetime.datetime.strptime(instructionTime, '%H:%M').time() 
		)
	)
	first_response_datetime = tzUser.localize(
		datetime.datetime.combine(  # combine tomorrow's date with the time to send the message
			tomorrowLocal, # tomorrow's date in user's tz
			datetime.datetime.strptime(exp["responseTimeLocal"], '%H:%M').time()  # the time of day to send the prompt datetime.datetime.strptime(instructionTime, '%H:%M').time() 
		)
	)
	# insert each trial into database.
	insert_result = []
	for ix, condition in enumerate(condition_array):
		insert_result.append(db_handle['trials'].insert_one({
			'fb_id': fb_id,
			'experiment_id': experiment_id,
			'trial_number': ix,
			'condition': condition,
			'instruction_sent': False,
			'response_request_sent': False,
			'response_given': False,
			'instruction_date': first_instruction_datetime + datetime.timedelta(hours=ix * exp["ITI"]), # add one day for each next trial. Will be transformed to UTC.
			'response_date': first_response_datetime + datetime.timedelta(hours=ix * exp["ITI"]), # ditto
			'created_at': datetime.datetime.utcnow(),
			'last_modified': datetime.datetime.utcnow(),
			'random_number': np.random.random(),
			'hash_sha256': hashlib.sha256(str(np.random.random())).hexdigest() # add a random hash, because if you don't add the np.random.random() then the same user doing experiment twice will go messed up
		}))
	return insert_result


def get_uncompleted_instructions(include_past=True, include_future=False, sort='chronological', limit=0):
	""" Looks at 'trials' database and return a list of uncompleted instructions 

	This should be useful e.g. for a CRON job to check if anything needs to be sent.

	Inputs
		include_past 		if True, includes uncompleted events in the past (before current time)
		include_future 		if True, includes uncompleted events in the future
		sort				how to sort the resulting list, should be 'chronological' or anything else for anti-chronological
		limit 				integer, maximum number of documents to return

	Returns
		instructions 		sorted list of dictionaries representing instructions
	"""
	# get current datetime in format that mongodb understands
	right_now = datetime.datetime.utcnow()
	if include_past and include_future:
		datesearch = {}
	elif include_past and not include_future:
		datesearch = {'instruction_date': {"$lte": right_now}}
	elif not include_past and include_future:
		datesearch = {'instruction_date': {"$gte": right_now}}
	elif not include_past and not include_future: # this is retarded of course
		datesearch = {'instruction_date': right_now}
	# update original query with additional constraints on what documents to return
	instruction_query = {'instruction_sent': False}
	instruction_query.update(datesearch)
	# set sort
	if sort == 'chronological':
		sort_as = pymongo.ASCENDING
	else:
		sort_as = pymongo.DESCENDING

	# get connection to database
	client, db, collection = open_connection(collectionName='trials')
	# execute query and return as list of dicts
	return list(collection.find(instruction_query).sort('instruction_date', sort_as).limit(limit))


def get_uncompleted_response_prompts(include_past=True, include_future=False, sort='chronological', limit=0):
	""" Looks at 'trials' database and return a list of uncompleted response prompts 

	This should be useful e.g. for a CRON job to check if anything needs to be sent.

	Inputs
		include_past 		if True, includes uncompleted events in the past (before current time)
		include_future 		if True, includes uncompleted events in the future
		sort				how to sort the resulting list, should be 'chronological' or anything else for anti-chronological
		limit 				integer, maximum number of documents to return

	Returns
		instructions 		sorted list of dictionaries representing response prompts
	"""
	# get current datetime in format that mongodb understands
	right_now = datetime.datetime.utcnow()
	if include_past and include_future:
		datesearch = {}
	elif include_past and not include_future:
		datesearch = {'response_date': {"$lte": right_now}}
	elif not include_past and include_future:
		datesearch = {'response_date': {"$gte": right_now}}
	elif not include_past and not include_future: # this is retarded of course
		datesearch = {'response_date': right_now}
	# update original query with additional constraints on what documents to return
	response_query = {'response_request_sent': False}
	response_query.update(datesearch)
	# set sort
	if sort == 'chronological':
		sort_as = pymongo.ASCENDING
	else:
		sort_as = pymongo.DESCENDING

	# get connection to database
	client, db, collection = open_connection(collectionName='trials')
	# execute query and return as list of dicts
	return list(collection.find(response_query).sort('response_date', sort_as).limit(limit))


def store_response(trial_hash, response):
	"""Stores a trial response and sets the flags to indicate response is received.

	Inputs
		trial_hash			should match a hash_sha256 in the 'trials' collection
		response 			a response in the format of the dependent variable of the experiment
	"""
	# open connection to trials database
	client, db_handle, trials_coll = open_connection(collectionName='trials')
	# check the has is in the database
	doc = trials_coll.find_one({"hash_sha256": trial_hash})
	if not doc: # if doc cannot be found
		print("could not find the document with hash %s" % trial_hash)
		return None
	# deposit result
	trials_coll.update_one({"hash_sha256": trial_hash}, {
		'$set': {
			'response_given': True,
			'trialRating': response
		},
		"$currentDate": {
			'last_modified': True
		}
	})


def send_outstanding_response_prompts():
	"""Uses get_uncompleted_response_prompts() to get to-do list, then sends emails.

	Returns number of emails sent

	"""
	outstanding = get_uncompleted_response_prompts(include_past=True, include_future=False)
	if not outstanding: # if list is empty
		print("no outstanding response prompts")
		return None
	print("number of outstanding response prompts: %d" % len(outstanding))

	client, db_handle, users_coll = open_connection(collectionName='users')
	trials_coll = db_handle["trials"]
	# at this stage there are outstanding response prompts
	for prompt in outstanding:
		# get the user
		user = users_coll.find_one({'_id': ObjectId(prompt['fb_id'])})
		result = email_defs.probe_meditation(trialHash=prompt['hash_sha256'], name=user['first_name'], email=user['email'])

		# store that instruction is sent, set the time instruction was sent, and update last_modified
		trials_coll.update_one({"_id": prompt["_id"]}, {
			"$set": {
				"response_request_sent": True
			}, 
			"$currentDate": {
				"response_request_sent_date": True, 
				"last_modified": True
			}
		})


def send_outstanding_instructions():
	"""Uses get_uncompleted_response_prompts() to get to-do list, then sends emails.

	"""
	outstanding = get_uncompleted_instructions(include_past=True, include_future=False)
	if not outstanding: # if list is empty
		print("no outstanding instructions")
		return None
	print("number of outstanding instructions: %d" % len(outstanding))

	client, db_handle, users_coll = open_connection(collectionName='users')
	trials_coll = db_handle["trials"]
	# at this stage there are outstanding response prompts
	for prompt in outstanding:
		# get the user
		user = users_coll.find_one({"_id": prompt['fb_id']})
		email_defs.instruct_meditation(name=user['first_name'], email=user['email'], condition=prompt['condition'])
		# store in the trials collection that the instruction has been sent and exact datetime
		trials_coll.update_one({"_id": prompt["_id"]}, {
			"$set": {
				"instruction_sent": True
			}, 
			"$currentDate": {
				"instruction_sent_date": True, 
				"last_modified": True
			}
		})


def trials_completed(filter={}):
	"""Returns number of completed trials for a particular filter.

	Queries the trials collection and looks for completed trials.
	Input
		filter 			passed to mongodb .find. Could e.g. filter by a particular experiment or user

	Returns
		integer with number of completed trials

	"""
	client, db_handle, trials_collection = open_connection(collectionName='trials')
	# construct the query for completed trials
	query = {
		'instruction_sent': True,
		'response_request_sent': True, 
		'response_given': True
		}
	# apply the filter
	query.update(filter)
	# search and return the number of retrieved docs
	return trials_collection.find(query).count()


def delete_user(_id):
	"""Delete a user
	
	Input
		_id			string, will be converted to ObjectId

	Returns
		DeleteResult result (.deleted_count)
	"""
	_, _, coll = open_connection(collectionName='users')
	return coll.delete_one({'_id': ObjectId(_id)})


def delete_experiment(_id):
	"""Delete an experiment

	Input
		_id 		string, will be converted to ObjectId

	Returns
		DeleteResult
	"""
	_, _, coll = open_connection(collectionName='experiments')
	return coll.delete_one({'_id': ObjectId(_id)})


def delete_trials(trial_list):
	"""Takes a list of trial id strings and delete these trials

	Input
		trial_list		an iterable that contains _id strings
	Returns
		a list of DeleteResults
	"""
	_, _, coll = open_connection(collectionName='trials')
	result = []
	for _id in trial_list:
		result.append(coll.delete_one({'_id': ObjectId(_id)}))
	return result


def unsubscribe_user(email):
	""" Remove outstanding trials and tag user as unsubscribed.

	If a user is registered for multiple experiment 
	"""
	# find all trials for this user across all experiments and delete them
	# Specifically, find all trials with outstanding response prompts
	client, db, coll = open_connection(collectionName='users')
	user_docs = list(coll.find({'email': email}))
	if not user_docs:
		print("no user found with this email address")
		email_defs.alert_zap(info="User with email %s tried to unsubscribe but when looking for the user in our database, I couldn't find them. Maybe look for them manually before they get pissed off for receiving more emails." % email)
		return(None)
	# assume user was found. Could be multiple signups under the same email, so get all user ids
	fb_ids = [doc['fb__id'] for doc in user_docs]
	# delete all trials associated with one of the user_ids, and have not had their response request sent
	db['trials'].delete_many({
		'fb_id': {'$in': fb_ids}, 
		'response_request_sent': False
	})

	# change the user to 'unsubscribed' and add date at which it happened
	coll.update_many({'email': email}, {
		'$set': {
			'subscribed': False
		},
		"$currentDate": {
			'last_modified': True,
			'unsubscribe_date': True, 
		}
	})


def fb_check_new_user(fb_id):
	""" Returns True if new, False if already exists

	user_id is a string that indicates the FACEBOOK user id
	Returns logical
	"""
	_, _, coll = open_connection(collectionName='users')
	return coll.find({'fb_id': fb_id}).count() == 0


def fb_store_user(first_name, second_name, fb_id, timezone='Europe/London'):
	""" Store user info in a collection. 
	As I understand it you don't have to sanitise inputs in MongoDB unless you're concatenating strings.
	Instead of using the has we can use the objectID in the mongoDB database, which is unique. 
	HOWEVER, IT MIGHT BE EASY TO PREDICT WHAT OTHER OBJECT IDS LOOK LIKE BASED ON YOUR OWN, so
	should probably start using a random string at some point. 
	
	Input:
		first_name 					string
		second_name 				string
		fb_id						string
	Returns:
		result 		contains unique id of user as insert_results.inserted_id
	"""
	
	client, db, collection = open_connection(collectionName='users')
	# write the user info to the database
	result = collection.insert_one({
		'first_name': first_name,
		'second_name': second_name,
		'fb_id': fb_id,
		'created_at': datetime.datetime.utcnow(),
		'last_modified': datetime.datetime.utcnow(),
		'timezone': timezone,
		'subscribed': True  # whether the user is active/subscribed
		})

	return result


def fb_delete_user(fb_id):
	"""Delete a user
	
	Input
		fb_id			string, will be converted to 

	Returns
		DeleteResult result (.deleted_count)
	"""
	_, _, coll = open_connection(collectionName='users')
	return coll.delete_one({'fb_id': fb_id})


def fb_init_experiment_meditation(fb_id, instructionTime=None, responseTime=None):
	""" Code to initialise the meditation experiment in the database. Helpful to identify what variables to store and how to name them
	
	Returns an instance of pymongo InsertOneResult, e.g. insert_result.inserted_id 
	to get the ID of inserted document
	"""
	# open a new connection
	client, db, collection = open_connection(collectionName='experiments')
	# fill with single experiment. Does not check for unique name 
	insert_result = collection.insert_one({
		'name': 'meditation',
		'conditions': ["meditate", "do not meditate"],
		'dependent_vars': ["happiness"],
		'nTrials': [10, 10],
		'ITI': 24, # set the ITI between trials in hours
		'randomise': 'max3', #how to randomise; see init_trials() for implementation
		'fb_id': fb_id,
		'instructionTimeLocal': instructionTime,  # store as string and only make into datetime when using it (mongo doesn't store properly)
		'responseTimeLocal': responseTime,
		'created_at': datetime.datetime.utcnow(),
		'last_modified': datetime.datetime.utcnow(),
	})
	return insert_result


def fb_update_experiment(fb_id, key, value):
	""" Update a user experiment with a new value
	Initially written to support updates to instruction and response time

	fb_id: string
	key: string indicating the key to update
	value: the new value
	"""
	print('Updating experiment record with ' + key + ' set to ' + str(value))
	_, _, collection = open_connection(collectionName='experiments')
	return collection.update_one({'fb_id': fb_id}, {
		'$set': {
			key: value
		},
		"$currentDate": {
			'last_modified': True
		}
	})


def fb_check_experiment_setup(fb_id):
	""" Check experiments for user and return what information is needed next

	Input:
		fb_id: string with user FB id
	Returns:
		string indicating what information is needed next. One of:
			instructionTime
			responseTime
			chocksAway (everything is complete and ready to set up experiment)
	"""

	print('CHECKING WHERE IN THE EXPERIMENT THE USER IS')

	# check how many experiments the user has
	_, _, collection = open_connection(collectionName='experiments')
	user_exp = collection.find({"fb_id": fb_id})
	print(str(user_exp.count()) + ' experiments found for user ' + fb_id)
	# if >1, something is wrong, so delete all and start over
	if user_exp.count() > 1:
		print('deleting experiment because theres more than one')
		collection.delete({"fb_id": fb_id})
	# if 0, set up new experiment with null times
	if user_exp.count() == 0:
		print('creating new experiment because theres none for this user')
		fb_init_experiment_meditation(fb_id)

	# user_exp may have changed to query again
	user_exp = collection.find_one({"fb_id": fb_id})
	print("PRINTING EXPERIMENT RECORD FOR THIS USER")
	print(user_exp)
	if user_exp['instructionTimeLocal'] is None:
		return 'instructionTime'
	elif user_exp['responseTimeLocal'] is None:
		return 'responseTime'
	else:
		return 'chocksAway'





# References
## Bulk operations in mongoDB: http://stackoverflow.com/a/36213728