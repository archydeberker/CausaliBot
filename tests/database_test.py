# TODO: implement tests for basic database functionality
# TODO: figure out how to mock the database

from database import db_utils


def test_open_connection():
    client, db, collection = db_utils.open_connection(collectionName='users')


def test_check_incomplete_instructions():
    incomplete = db_utils.get_uncompleted_instructions()


def test_check_incomplete_prompts():
    incomplete = db_utils.get_uncompleted_response_prompts()


def test_send_outstanding_prompts():
    db_utils.fb_send_outstanding_response_prompts()


def test_create_experiment():
    pass


def test_record_response():
    pass


def test_send_prompt():
    pass


def test_store_response_attempt():
	assert(db_utils.store_response_attempt('fake FB id', 3) == None)
	assert(db_utils.store_response_attempt('123456', 'this is not an int rating') == None)