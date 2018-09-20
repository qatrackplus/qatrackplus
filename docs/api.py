import base64
import requests

root = "http://127.0.0.1/api"
token_url = root + "/get-token/"
resp = requests.post(token_url, {'username': 'randlet', 'password': '***REMOVED***'})
api_token = resp.json()['token']

# the request headers must include the API token
headers = {"Authorization": "Token %s" % api_token}

unit_name = "TB1"
test_list_name = "Picket Fence"
url = root + '/qa/unittestcollections/?unit__name=%s&test_list__name=%s' % (unit_name, test_list_name)

# find the UnitTestCollection we want to perform
resp = requests.get(url, headers=headers)
utc_url = resp.json()['results'][0]['url']

# prepare the data to submit to the API. Binary files need to be base64 encoded before posting!
data = {
    'unit_test_collection': utc_url,
    'work_started': "2018-09-19 10:00",
    'work_completed': "2018-09-19 10:30",
    'comment': "Performed via the API!",  # optional
    'tests': {
        'pf_upload_analysis': {  # pf_upload_analysis is the name of our upload test
            'filename': 'picket.dcm',
            'value': base64.b64encode(open("/home/randlet/Downloads/picket.dcm", 'rb').read()).decode(),
            'encoding': 'base64'
        },
    },
    'attachments': []  # optional
}

# send our data to the server
resp = requests.post(root + "/qa/testlistinstances/", json=data, headers=headers)

if resp.status_code == requests.codes.CREATED: # http code 201
    completed_url = resp.json()['site_url']
    print("Test List performed successfully! View your Test List Instance at %s" % completed_url)
else:
    print("Your request failed with error %s (%s)" % (resp.status_code, resp.reason))
