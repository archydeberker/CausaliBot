# TODO: implement tests for integration with other services

from database import wit

def test_wit():
    output = wit.understand_string('7am')
    assert output['_text'] == '7am'
    assert wit.timestamp_to_simple_string(output) == '07:00'


def test_giphy():
    pass


def test_facebook_hook():
    pass
