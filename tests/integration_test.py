# TODO: implement tests for integration with other services

from database import wit
from database import msg

def test_wit():
    output = wit.understand_string('7am')
    assert output['_text'] == '7am'
    assert wit.timestamp_to_simple_string(output) == '07:00'


def test_giphy():
    pass


def test_facebook():

    archy_id = '1268264959927583'
    msg.send_quick_reply_rating(archy_id, 'Archy, this is an integration test', 'integration_test', point_range=(0, 10), trial_hash='no_trial')

