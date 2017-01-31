"""This doc contains data - messages that we can cycle through.
Also contains one function to give you a random element
"""

import random

messages = {
	'greeting' : ['Hi', 'Hey', 'Hola'],
	'offensive': ['retard', 'dickhead', 'numbnuts']
	}


def rnd(var):
	""" var is the name you want a random element from
	"""
	return random.choice(messages[var])
