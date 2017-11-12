
import os
import requests


API_HOST = os.environ.get('API_HOST', 'localhost')
API_PORT = os.environ.get('API_PORT', '5000')

base_url = "http://{}:{}/".format(API_HOST, API_PORT)
base_path = os.path.abspath(os.path.dirname(__file__))

def test_ping(self):
    res = requests.get(base_url + "ping")
    assert res.content == 'pong'
    assert res.status_code == 200

