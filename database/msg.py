"""This doc contains data - messages that we can cycle through.
Also contains one function to give you a random element
"""

import random
import urllib2
import urllib
import json
import sys
import os
import requests
from matplotlib import pyplot as plt


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()
    

def rnd_text_string(var):
	""" var is the name you want a random element from.
	Example: msg.rnd('greeting')
	"""
	messages = {
	'greeting' : ['Hi', 'Hey', 'Hola'],
	}
	return random.choice(messages[var])


def rnd_gif(tag=''):
	""" get random Giphy gif, or random based on tag given. 
	https://github.com/Giphy/GiphyAPI#random-endpoint

	Returns the URL of the gif

	TODO make the gif actually random, check that the arguments here are not also global/packages making the code return the same gif over and over. 

	"""
	
	# uses a public beta API key
	query_fields = {
		'api_key': 'dc6zaTOxFJmzC', 
		'tag': tag,
		'rating': 'g'  # no offensive gifs
		}
	request_object = urllib2.Request('http://api.giphy.com/v1/gifs/random?' + urllib.urlencode(query_fields))
	response_object = urllib2.urlopen(request_object)

	if response_object.getcode() == 200:  # means success
		msg_content = json.loads(response_object.read())
		giphy_url = msg_content['data']['image_url']
		print('URL retrieved from Giphy:', giphy_url)
		# use image_url instead of URL so Facebook recognises it's a gif.
		return giphy_url
	else:
		print('Request to Giphy failed with code')
		print('Status code:', response_object.getcode())  # print the code
		return ''


def send_plain_text(fb_id, message_text):
    '''Send plain text message to recipient through facebook.

    Documentation: https://developers.facebook.com/docs/messenger-platform/send-api-reference/text-message

    '''
    log("sending message to {recipient}: {text}".format(recipient=fb_id, text=message_text))
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": fb_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_image(fb_id, image_url=None):
    """ Sends an image at the location of the image_url. 

    Facebook docs: https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment

    If none given, sends a random giphy science gif. The reason to use image_url=None instead of calling rnd_gif 
    in the function definition is that it will always use the same gif if rnd_gif() is used in the function def!
    """
    if image_url is None:
        image_url = rnd_gif(tag='science')

    log("sending IMAGE to {recipient}: {text}".format(recipient=fb_id, text=image_url))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": fb_id
        },
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url
                }
            }
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_local_image(fb_id, local_path):
    """Send image stored locally to user"""
    log("sending local image to {recipient}: {text}".format(recipient=fb_id, text=local_path))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": fb_id
        },
        "message": {
            "attachment": {
                "type": "file",
                "payload": {}
            }
        },
        "filedata": open(local_path, 'rb')
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_quick_reply(fb_id, prompt, quick_replies):
    ''' Give someone a few options to pick from
    https://developers.facebook.com/docs/messenger-platform/send-api-reference/quick-replies

    Note that the response to this message comes in through the Message Received callback. 

    Input
    	fb_id		        string with facebook ID
    	prompt 				string with prompt
    	quick_replies		list of dicts, each dict has content_type, title, payload, and optional image_url. Payload should be a json

    Example quick_replies:
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
    '''
    log("sending quick reply to {recipient}: {text}".format(recipient=fb_id, text=prompt))
    assert all([len(json.loads(dic['payload'])) == 1 for dic in quick_replies]), "All payload items should be a dict with a single key indicating the question"
    assert len(set([json.loads(dic['payload']).keys()[0] for dic in quick_replies])) == 1, "All payload items should have the same key in the dict indicating the question type"
    
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": fb_id
        },
        "message": {
            "text": prompt,
            "quick_replies": quick_replies
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_quick_reply_rating(fb_id, prompt, question_identifier, point_range=(0, 10), trial_hash='no_trial'):
    ''' Sends a quick reply rating request for a specific trial. 
    Example function call taken from fb_send_outstanding_response_prompts:
        msg.send_quick_reply_rating(
            fb_id=prompt['fb_id'], 
            prompt="How calm are you feeling right now %s?" % user['first_name'], 
            question_identifier='trial_response',  # this will be the key that identifies this is a trial response
            point_range=(0, 10),
            trial_hash=prompt['hash_sha256']  # this identifies the trial and will be used in the payload as well
            )

    Args
        prompt                  string with prompt
        question_identifier     used in the payload to identify the question - make it something intelligible. This will be used in app.py. 
        point_range             tuple with bounds for range of allowable answers. 
        trial_hash              if this concerns a trial, set the hash. Otherwise string with 'no_trial'

    '''
    quick_replies = [
        {'content_type': 'text', 'title': str(rating), 'payload':json.dumps({question_identifier: {'trial_hash': trial_hash, 'rating': str(rating)}})} 
        for rating in range(point_range[0], point_range[1]+1)
    ]
    send_quick_reply(fb_id, prompt, quick_replies)


def send_experiment_results(fb_id):
    """Send an image with current results"""
    directory = 'tmp'
    if not os.path.exists(directory):
        os.makedirs(directory)
    filepath = os.path.join(directory, str(fb_id) + '.png')

    plt.plot([0, 1, 2, 3, 4], [0, 3, 5, 9, 11])
    plt.savefig(filepath, bbox_inches='tight')
    send_local_image(fb_id, filepath)

