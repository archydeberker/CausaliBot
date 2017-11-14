import os

from database import wit
from database import msg

testing_fb_id = os.environ.get('TESTING_FB_ID')


def test_wit():
    output = wit.understand_string('7am')
    assert output['_text'] == '7am'
    assert wit.timestamp_to_simple_string(output) == '07:00'


def test_giphy():
    gif_url = msg.rnd_gif()
    assert gif_url is not None


def test_quick_reply_facebook():
    msg.send_quick_reply_rating(testing_fb_id, 'Archy, this is a quick reply integration test', 'integration_test', point_range=(0, 10), trial_hash='no_trial')


def test_prompt_facebook():
    msg.send_plain_text(testing_fb_id, 'Archy, this is a plain test integration test')


def test_gif_facebook():
    gif_url = msg.rnd_gif()
    msg.send_image(testing_fb_id, gif_url)


