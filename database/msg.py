"""This doc contains data - messages that we can cycle through.
Also contains one function to give you a random element
"""

import random
import urllib2
import urllib
import json


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


def send_plain_text(recipient_id, message_text):
    '''Send plain text message to recipient through facebook.

    Documentation: https://developers.facebook.com/docs/messenger-platform/send-api-reference/text-message

    '''
    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_image(recipient_id, image_url=None):
    """ Sends an image at the location of the image_url. 

    Facebook docs: https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment

    If none given, sends a random giphy gif
    """
    if image_url is None:
        image_url = rnd_gif(tag='science')

    log("sending IMAGE to {recipient}: {text}".format(recipient=recipient_id, text=image_url))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
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


def send_quick_reply(recipient_id, prompt, quick_replies):
    ''' Give someone a few options to pick from
    https://developers.facebook.com/docs/messenger-platform/send-api-reference/quick-replies

    Note that the response to this message comes in through the Message Received callback. 

    Input
    	recipient_id		string with facebook ID
    	prompt 				string with prompt
    	quick_replies		list of dicts, each dict has content_type, title, payload, and optional image_url

    Example quick_replies:
    quick_replies = [
      {
        "content_type":"text",
        "title":"Red",
        "payload":"red"
      },
      {
        "content_type":"text",
        "title":"Green",
        "payload":"green"
      }
    ]
    '''
    log("sending quick reply to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text,
            "quick_replies": quick_replies
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)