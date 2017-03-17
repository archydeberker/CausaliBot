	# import packages
import sys
import os
import json
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
from database import msg


# find the database URI. If not available in the environment, use local mongodb host
URI = os.getenv('MONGODB_URI', 'mongodb://localhost')
# get the name of the database: either causali or causali-staging (or localhost).
db = URI.split('/')[-1]

def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


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


def coll(collection_name):
	"""Return pymongo object pointing towards the collection
	You can use this for example like so:
		coll('users').find({'fb_id': fb_id})

	"""
	_, _, coll = open_connection(collectionName=collection_name)
	return coll


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


	# execute query and return as list of dicts
	return list(coll('trials').find(instruction_query).sort('instruction_date', sort_as).limit(limit))


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

	# execute query and return as list of dicts
	return list(coll('trials').find(response_query).sort('response_date', sort_as).limit(limit))


def store_response(trial_hash, response):
	"""Stores a trial response and sets the flags to indicate response is received.

	Inputs
		trial_hash			should match a hash_sha256 in the 'trials' collection
		response 			a response in the format of the dependent variable of the experiment
	"""

	# check the has is in the database
	doc = coll('trials').find_one({"hash_sha256": trial_hash})
	if not doc: # if doc cannot be found
		log("could not find the document with hash %s" % trial_hash)
		return None
	# deposit result
	return coll('trials').update_one({"hash_sha256": trial_hash}, {
		'$set': {
			'response_given': True,
			'trialRating': response
		},
		"$currentDate": {
			'last_modified': True
		}
	})


def fb_send_outstanding_response_prompts():
	"""Uses get_uncompleted_response_prompts() to get to-do list, then sends messages.

	Returns number of emails sent

	"""
	outstanding = get_uncompleted_response_prompts(include_past=True, include_future=False)
	if not outstanding: # if list is empty
		log("no outstanding response prompts")
		return None
	log("number of outstanding response prompts: %d" % len(outstanding))

	# at this stage there are outstanding response prompts
	for prompt in outstanding:
		# get the user
		user = coll('users').find_one({'fb_id': prompt['fb_id']})
		# send the message
		msg.send_quick_reply_rating(
			fb_id=prompt['fb_id'], 
			prompt="How calm are you feeling right now %s?" % user['first_name'], 
			question_identifier='response_prompt',  # this will be the key that identifies this is a trial response
			point_range=(0, 10),
			trial_hash=prompt['hash_sha256']  # this identifies the trial and will be used in the payload as well
			)


		# store that instruction is sent, set the time instruction was sent, and update last_modified
		coll('trials').update_one({"hash_sha256": prompt["hash_sha256"]}, {
			"$set": {
				"response_request_sent": True
			}, 
			"$currentDate": {
				"response_request_sent_date": True, 
				"last_modified": True
			}
		})


def fb_send_outstanding_instructions():
	"""Uses get_uncompleted_response_prompts() to get to-do list, then sends facebook messages telling people to meditate or not.

	"""
	outstanding = get_uncompleted_instructions(include_past=True, include_future=False)
	if not outstanding: # if list is empty
		log("no outstanding instructions")
		return None
	log("number of outstanding instructions: %d" % len(outstanding))

	# at this stage there are outstanding response prompts
	for prompt in outstanding:
		# get the user
		user = coll('users').find_one({"fb_id": prompt['fb_id']})
		# send the message	
		msg.send_plain_text(
			prompt['fb_id'], 
			"Hey %s, hope you're having a great day. As part of your meditation experiment with Causali, today you should %s" % (user['first_name'], prompt['condition'].lower()))

		# store in the trials collection that the instruction has been sent and exact datetime
		coll('trials').update_one({"hash_sha256": prompt["hash_sha256"]}, {
			"$set": {
				"instruction_sent": True
			}, 
			"$currentDate": {
				"instruction_sent_date": True, 
				"last_modified": True
			}
		})


def fb_instruct_meditation(name, fb_id, condition):
	"""Instructs a user to do condition.

	Inputs
		Name
		Email
		string which represents this trial's condition
	Returns
		result 		should contain info about whether message was successfully sent. Not sure what is in it
	"""

	msg.send_plain_text(fb_id, "Hope you're having a great day. As part of your meditation experiment with Causali, today you should %s"%condition.lower())

	return result


def fb_user_check_experiment_signup_status(fb_id):
	""" Returns 'no experiment', 'instructionTime', 'responseTime', 'complete', 'multiple'

	"""
	user_exp = coll('experiments').find({"fb_id": fb_id})
	if user_exp.count() == 0:
		return 'no experiment'
	elif user_exp.count() > 1:
		return "multiple"

	# another trip to mongo
	exp = user_exp.next()
	if exp['instructionTimeLocal'] is None:  # experiment does not have an instruction time set
		return 'instructionTime'
	elif exp['responseTimeLocal'] is None:  # experiment does not have a response time set
		return 'responseTime'
	else:
		return 'complete'  # if those two times are set, the experiment setup is complete




def fb_init_experiment_meditation(fb_id, instructionTime=None, responseTime=None):
	""" Code to initialise the meditation experiment in the database. Helpful to identify what variables to store and how to name them
	
	Returns an instance of pymongo InsertOneResult, e.g. insert_result.inserted_id 
	to get the ID of inserted document
	"""
	# fill with single experiment. Does not check for unique name 
	insert_result = coll('experiments').insert_one({
		'name': 'meditation',
		'conditions': ["meditate", "not meditate"],
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


def fb_init_trials(fb_id):
	""" Initialises all the trials for an experiment for a user, reading a document in the 'experiments' database and populating the 'trials' collection.

	This assumes that the experiment already exists in the database, and simply reads out the experiments and makes sure all reminders are set, timezones are corrected for,
	and order of conditions is randomised.

	Timezones
	Facebook gives you offset from UTC, not the timezone. So we need to store our times in UTC.

	Inputs
		fb_id 			string, FACEBOOK id
		experiment_id 	string, not an ObjectId

	Returns
		bool indicating success (True) or failure (False)
	"""

	# get information about the experiment and store it into the variable
	exp = coll('experiments').find_one({"fb_id": fb_id})
	# get user object from database
	user = coll('users').find_one({"fb_id": fb_id})
	
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
		log('did not reach criterion for randomising; using current state of condition_array instead')
	
	# make a pytz object to localise the dates and times. Some crucial notes on timezones:
	# - Once a date-aware object is written to Mongo it will be transformed to UTC. 
	# - create a timezone object using pytz.timezone('string')
	# - Transform an existing tz-aware datetime to another timezone using .astimezone(tz_object)
	tzUser = pytz.timezone(get_approx_timezone(user['timezone_offset']))
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
		# ensure unique-ness. Burdensome on database but if this goes badly (or e.g. heroku resets the seed on every boot) it is all fucked.
		unique = False
		while not unique:
			hash = hashlib.sha256(str(np.random.random())).hexdigest()
			if coll('trials').find({'hash_sha256': hash}).count() == 0:
				unique = True

		insert_result.append(coll('trials').insert_one({
			'fb_id': fb_id,
			'experiment_id': exp['_id'],
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
			'hash_sha256': hash # add a random hash
		}))

	return True


def fb_update_experiment(fb_id, key, value):
	""" Update a user experiment with a new value
	Initially written to support updates to instruction and response time

	fb_id: string
	key: string indicating the key to update
	value: the new value
	"""
	return coll('experiments').update_one({'fb_id': fb_id}, {
		'$set': {
			key: value
		},
		"$currentDate": {
			'last_modified': True
		}
	})


def get_approx_timezone(offset):
	''' Get a possible timezone based on a user offset.

	Assumes utc if it can't detect the timezone.

	Will not be always correct but will do a decent job for now.

	Args
		offset 		a number or string indicating offset

	Returns
		tz 			a pytz timezone object
	'''

	utc_offset = datetime.timedelta(hours=offset)  # +5:30
	now = datetime.datetime.now(pytz.utc)  # current time
	tz = [tz.zone for tz in map(pytz.timezone, pytz.all_timezones_set) if now.astimezone(tz).utcoffset() == utc_offset][0]
	if len(tz) == 0:
		tz = pytz.utc

	return tz


def parse_quick_reply(messaging_event):
    ''' First port of call when a quick reply comes in. 

    Now let us agree that payload should always be a dictionary of which
    the first key defines what message this was a response to, and the value of that
    key contains all the information to process the response.
    For example: the key of the payload might be colour_picker, which identifies the QUESTION. 
    We then know what to do when the payload comes back to us. 
    quick_replies = [
      {
        "content_type":"text",
        "title":"Red",
        "payload":"{'colour_picker': 'red'}"
      },
      {
        "content_type":"text",
        "title":"Green",
        "payload":"{'colour_picker': 'red'}"
      }
    ]
    Or for a trial, make the KEY trial_response - so we know it's a response to a trial -
    and store the trial hash and the response in the dict value. 


    Args
        messaging_event         contains the contents and metadata of the message

    Return
        question        string with the question identifier
        response        the value for the answer provided in the original payload
    '''
    # this is the payload defined for this answer
    payload = json.loads(messaging_event['message']['quick_reply']['payload'])

    assert len(payload) == 1, "Was expecting payload to only have a single key indicating the question"
    question = payload.keys()[0]
    response = payload[question]
    return question, response


def check_response_after_instruction(fb_id, responseTime):
	''' Check if the string in responseTime is after this user's instructionTime

	'''
	exp = coll('experiments').find_one({'fb_id': fb_id})
	return string_to_datetime_hour_minute(exp['instructionTimeLocal']) < string_to_datetime_hour_minute(responseTime)


def string_to_datetime_hour_minute(string):
	# convert string timestamp (e.g. '07:00') to datetime object
	return datetime.datetime.strptime(string, '%H:%M')


class User(object):
	''' This is a User object which handles user-level operations. Not all of these are refactored into this class yet.

	Guide on classes:
	https://jeffknupp.com/blog/2014/06/18/improve-your-python-python-classes-and-object-oriented-programming/
	
	Args
		fb_id 		facebook ID of the user
	'''

	def __init__(self, fb_id):
		self.fb_id = fb_id


	def exists(self):
		""" Returns True if exists in db, False if does not exist
		"""
		return coll('users').find({'fb_id': self.fb_id}).count() == 1


	def create(self, first_name, second_name, fb_id, timezone_offset=0):
		""" Store user info in a collection. 
		
		Input:
			first_name 					string
			second_name 				string
			fb_id						string
			timezone_offset				integer indicating hours from UTC
		Returns:
			result 		contains unique id of user as insert_results.inserted_id
		"""
		
		# write the user info to the database
		result = coll('users').insert_one({
			'first_name': first_name,
			'second_name': second_name,
			'fb_id': self.fb_id,
			'created_at': datetime.datetime.utcnow(),
			'last_modified': datetime.datetime.utcnow(),
			'timezone_offset': float(timezone_offset),
			'timezone': get_approx_timezone(float(timezone_offset)),
			'subscribed': True  # whether the user is active/subscribed
			})

		return result


	def count_completed_trials(self):
		"""Return integer with number of completed trials"""
		
		# construct the query for completed trials
		query = {
			'instruction_sent': True,
			'response_request_sent': True, 
			'response_given': True,
			'fb_id': self.fb_id
			}

		# search and return the number of retrieved docs
		return coll('trials').find(query).count()


	def destroy_everything(self):
		"""remove anything related to the user, including completed items"""
		coll('users').delete_many({'fb_id': self.fb_id})
		coll('trials').delete_many({'fb_id': self.fb_id})
		coll('experiments').delete_many({'fb_id': self.fb_id})
		coll('user_logs').delete_many({'fb_id': self.fb_id})


	def delete_future_trials(self):
		"""Remove any outstanding trials but preserve existing data"""
		for trial in self.list_incomplete_trials():
			coll('trials').delete_one({'hash_sha256': trial['hash_sha256']})


	def delete_trials(self):
		"""remove all trials, including ones with data"""
		return coll('trials').delete_many({'fb_id': self.fb_id})


	def delete_experiments(self):
		""" Delete the experiments associated with this user
		"""
		return coll('experiments').delete_many({'fb_id': self.fb_id})


	def list_incomplete_trials(self):
		"""Get list of all incomplete trials"""
		return list(coll('trials').find({
			'fb_id': self.fb_id,
			'response_given': False
			}))


	def update(self, key, value):
		""" Update a user with a new value
		Initially written to support updates to instruction and response time

		key: string indicating the key to update
		value: the new value
		"""
		return coll('users').update_one({'fb_id': self.fb_id}, {
			'$set': {
				key: value
			},
			"$currentDate": {
				'last_modified': True
			}
		})


	def log_entry(self, key, value):
		'''Store a log item for a user. Note that value can sometimes be the current time (if user uses)
		the keyword 'time'.

		'''
		return coll('user_logs').insert_one({
			'fb_id': self.fb_id,
			'created_at': datetime.datetime.now(pytz.utc),
			key: value
			})

