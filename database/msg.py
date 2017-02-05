"""This doc contains data - messages that we can cycle through.
Also contains one function to give you a random element
"""

import random
import urllib2
import urllib
import json



def rnd(var):
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
	query = {
		'api_key': 'dc6zaTOxFJmzC', 
		'tag': tag,
		'rating': 'g'  # no offensive gifs
		}
	rq = urllib2.Request('http://api.giphy.com/v1/gifs/random?' + urllib.urlencode(query))
	resp = urllib2.urlopen(rq)

	if resp.getcode() == 200:  # means success
		msg_content = json.loads(resp.read())
		# use image_url instead of URL so Facebook recognises it's a gif.
		return msg_content['data']['image_url']
	else:
		print('Request to Giphy failed with code')
		print('Status code:', resp.getcode())  # print the code
		return ''
