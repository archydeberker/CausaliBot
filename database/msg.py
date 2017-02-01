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
	"""
	# uses a public beta API key
	query = {'api_key': 'dc6zaTOxFJmzC', 'tag': urllib.urlencode(tag)}
	rq = urllib2.Request('http://api.giphy.com/v1/gifs/random?' + urllib.urlencode(query))
	resp = urllib2.urlopen(rq)

	if resp.getcode() == 200:  # means success
		msg = json.loads(resp.read())
		return msg['data']['url']
	else:
		print('Request to Wit failed for message:', message_text)
		print('Status code:', resp.getcode())  # print the code
		return ''
