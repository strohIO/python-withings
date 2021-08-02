
from datetime import datetime
from datetime import timedelta
import json
from pprint import pprint
import sys
import threading
import urllib

from bs4 import BeautifulSoup
import requests

from .callback import Oath2CallbackServer
from .variables import MEAS_CODES



def get_url_params(url_path):
    split_path = url_path.split('?')

    if len(split_path) != 2:
            raise Exception("No parameter query in url.")

    parsed_parms = urllib.parse.parse_qs(split_path[1])

    return { k:v[0] for k,v in parsed_parms.items() }





class WithingsAUTH:

    def __init__(self, client_id, callback_url):#, user_email=None, password=None):

        self.session = requests.Session()

        # self.callback_url = callback_url
        # self.client_id = client_id
        # self.user_email = user_email
        # self.password = password

        self.headers = {
            'Host': 'account.withings.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        self.parms = {
            'response_type': 'code',
            'client_id': client_id,
            'state': "HAHAHA",
            # Scale - user.metrics
            # Sleep - user.activity
            'scope': 'user.info,user.metrics,user.activity',
            'redirect_uri': callback_url,
            'b': 'authorize2',
        }


    def _call(self, verb: str, route: str, payload=None):

        if payload:
            payload = urllib.parse.urlencode(payload)
        
        response = self.session.request(method=verb,
                                        url="https://account.withings.com/oauth2_user/{}".format(route),
                                        params=urllib.parse.urlencode(self.parms),
                                        headers=self.headers,
                                        data=payload)

        return response


    def _get_csrf_token(self):

        response = self._call('get', 'account_login')

        # if routed response comes up with 'selecteduser' param, save value
        if 'selecteduser' in response.url:
            query = get_url_params(response.url)
            self.parms['selecteduser'] = query['selecteduser']
            print('selecteduser acquired.')

        # Extract csrf_token value from html element
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name':'csrf_token'})['value']
        #self._csrf_token = csrf_token

        print('CSRF_TOKEN acquired.')

        return csrf_token


    def _sign_in(self, csrf_token: str, user_email, password):
        
        body = {
            'email': user_email,
            'password': password,
            'is_admin': 'f',
            'csrf_token': csrf_token,
        }

        response = self._call("post", "account_login", body)
        # check response.status_code for failed logins
        if 'session_key' not in self.session.cookies:
            print(response.url)
            raise Exception#("Sign-in error: no session_key provided. \
                            # Was there already too many failed attempts?")

        print('SESSION_KEY Cookie acquired')

        return self.session.cookies['session_key']


    def _authorize(self, csrf_token):

        body = {
            'authorized': 1,
            'csrf_token': csrf_token,
        }

        response = self._call("post", "authorize2", body)

        print('Authorization Code acquired')

        # can also get code from response.url
        # potentially, one could forego a server, catch the ConnectionError, 
        # and simply read the 'location' header
        return response.json()['code']
        #except (ConnectionResetError, ProtocolError, requests.exceptions.ConnectionError):


    def get_auth_code(self, user_email, password):

        # GET:  grab csrf_token from a hidden element in the html on the ACCOUNT_LOGIN page
        csrf_token = self._get_csrf_token()

        # POST: attach that csrf to body along with creds to post to basically that same URL
        self._sign_in(csrf_token, user_email, password)

        # GET: grab new csrf_token, but with the session_id cookie included from the previous call
        #       to be taken to the 'Allow this app?' page
        new_csrf_token = self._get_csrf_token()

        # Start up server in background to listen for callback request containing the authorization code
        #  which is then forwarded back to the caller.
        evt = threading.Event()
        callback_handler = Oath2CallbackServer(evt)
        callback_handler.start()
        # Wait until the server is loaded up before kicking off the callback api
        evt.wait()

        # Request Authorization Code. Pulls from own server after redirect.
        #  Posts to the AUTHORIZE2 page, which forwards to the above CallbackServer, with a 'code' query 
        #  parameter, which the CallbackServer reads and returns back to this authorize response.
        code = self._authorize(new_csrf_token)

        # Ensure server finishes before proceeding
        callback_handler.join()
        print("Authorization complete.") # log.INFO

        # This authorization code is passed to the API to get the access token & refresh token.
        return code



class Withings:
    '''
    access_token is valid for three hours.
    Use refresh_token to get a new access_token after it expires.'''

    def __init__(self, client_id, client_secret, 
                 callback_url, auth_code=None, 
                 access_token=None, refresh_token=None):

        if not auth_code and not (access_token and refresh_token):
            raise Exception("Either auth_code, or access_token & refresh_token must be given.")
        elif auth_code and access_token and refresh_token:
            raise Exception("Only auth_code, or access_token & refresh_token must be given.")

        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_code = auth_code
        self.callback_url = callback_url
        self.access_token = access_token
        self.refresh_token = refresh_token

    def authenticate(self):

        body = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': self.auth_code,
            'redirect_uri': self.callback_url,  # What is the redirect_uri for here?
        }

        response = requests.post(url='https://account.withings.com/oauth2/token',
                                 data=body)

        data = response.json()

        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.expires_in = datetime.now() + timedelta(seconds=data['expires_in'])
        
        self.userid = data['userid']
        self.scope = data['scope']

        self.headers = { "Authorization": "Bearer {}".format(self.access_token) }
        
        return self


    def get_devices(self):

        if not self.access_token:
            raise Exception("Access Token not set yet.")


        parms = { "action": "getdevice" }

        response = requests.get('https://wbsapi.withings.net/v2/user',
                                 headers=self.headers,
                                 params=parms)
        return response.json()


    def get_measurements(self, type_name: str):
        if not self.access_token:
            raise Exception("Access Token not set yet.")

        parms = { "action": "getmeas" }

        hdrs = self.headers

        if type_name:
            hdrs['type'] = str(MEAS_CODES[type_name])

        response = requests.get('https://wbsapi.withings.net/measure',
                               headers=hdrs,
                               params=parms)

        measurements = response.json()

        # Replace type-codes with type-names
        for record in measurements['body']['measuregrps']:
            for measure in record['measures']:
                measure['type'] = MEAS_CODES.inverse[measure['type']]

        return measurements['body']['measuregrps']

    
    def get_sleep_data(self, 
                       start_date=datetime(year=2019, month=5, day=16), 
                       end_date=datetime.now() + timedelta(days=1)):
        '''
        First viable startdate is default.
        Tomorrow is default enddate, to ensure latest night's data.
        If end_date > 24hrs after start_date, the API will instead use 24hrs after specified start_date.
        '''
        if not self.access_token:
            raise Exception("Access Token not set yet.")

        parms = {
            "action": "get",
            "startdate": start_date.strftime('%s'),
            "enddate": end_date.strftime('%s'),
            #"data_fields": 'hr,rr,snoring',
        }

        print('Recieving data between {} and {}'.format(start_date.date(), end_date.date()))

        response = requests.get('https://wbsapi.withings.net/v2/sleep',
                                headers=self.headers,
                                params=parms)
        
        print('Data recieved between {} and {}'.format(start_date.date(), end_date.date()))
        
        results = response.json()
        
        if 'series' not in results['body']:
            print('ERROR:','No body/series in results.')
            print(response.text)
            return []

        return response.json()['body']['series']


    def get_sleep_detail_data(self, 
                       start_date=None, 
                       end_date=None,
                       last_update_date=None):
        '''
        If 'more'=True and 'offset'>0 in result['body'], then offset value is the 
        number of returned data from the current request, and there is more data available.
        Seems like this API returns MAX 300 records per request.
        '''

        if not self.access_token:
            raise Exception("Access Token not set yet.")

        parms = {
            "action": "getsummary",
            #"data_fields": 'hr,rr,snoring',
        }

        if (start_date and end_date) and not last_update_date:
            parms["startdate"] = start_date.strftime('%s')
            parms["enddate"] = end_date.strftime('%s')

        elif last_update_date and (not start_date and not end_date):
            parms["lastupdate"] = last_update_date.strftime('%s')

        else:
            raise Exception("Either last_update_date or start & end dates should be provided.")

        response = requests.get('https://wbsapi.withings.net/v2/sleep',
                                headers=self.headers,
                                params=parms)
        
        results = response.json()
        
        # if 'series' not in results['body']:
        #     print('ERROR:','No body/series in results.')
        #     pprint(response.text)
        #     return []

        return response.json()['body']['series'], response.json()['body']['more']
