# Send a test email of specified type

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), os.pardir)))
import db_utils as db
from mail.email_defs import confirm_signup_meditation,instruct_meditation, probe_meditation

emailType 			= sys.argv[1]
emailAddress 		= sys.argv[2]
trialHash			= '0000'

print(emailType, emailAddress)

if emailType=='probe':
	probe_meditation('test', emailAddress, trialHash)
	print("Probe email sent")
elif emailType=='instruct':
	instruct_meditation('test', emailAddress, 'meditate')
elif emailType=='signup':
	confirm_signup_meditation('test', emailAddress)


print("Finished signup_meditation.py")