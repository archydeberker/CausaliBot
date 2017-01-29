# set of functions to interact with the Wit AI

def understand_string(message_text):
	# send a string to wit and get structured info back.
	# For list of headers see https://www.cs.tut.fi/~jkorpela/http.html
	# Returns a dictionary if the call was successful
	rq = urllib2.Request('https://api.wit.ai/message?v=20170129&q='+message_text)
	rq.add_header("Authorization", "Bearer FS4CJQVZGWFNJ525V5JJ7NVR5SWBDUIG")
	rq.add_header('Content-Type', 'text/plain')

	resp = urllib2.urlopen(rq)
	if resp.getcode() == 200:  # means success
		msg = resp.read()
    	return json.loads(msg)
	else:  # not successful
		print('Request to Wit failed for message:', message_text)
		print('Status code:', resp.getcode())  # print the code
		return {}