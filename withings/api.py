
from datetime import datetime
from datetime import timedelta
from functools import partialmethod
import json
from math import floor
from pprint import pprint
import sys
from threading import Event
from threading import Lock

from dateutil.parser import parse
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests_oauthlib import OAuth2Session

from .codes import MeasureType, SleepState
from .exceptions import AuthenticationFailedException
from .exceptions import raise_for_status as withings_raise_for_status



class WithingsOath2Client:
    '''
    access_token is valid for three hours.
    Use refresh_token to get a new access_token after it expires.
    '''

    def __init__(self, client_id, client_secret, callback_url,
                 auth_code=None, access_token=None, 
                 refresh_token=None, expires_at=None,
                 token_updater=None):

        if not auth_code and not (access_token and refresh_token and expires_at):
            raise Exception("Either auth_code, or access_token & refresh_token & expires_at must be given.")
        elif auth_code and access_token and refresh_token:
            raise Exception("Only auth_code, or access_token & refresh_token must be given.")

        self.client_id = client_id
        self.client_secret = client_secret

        self.auth_code = auth_code
        self.callback_url = callback_url
        self.access_token = access_token
        self.refresh_token = refresh_token

        # Handle setting expires_at value to float timestamp
        try:
            self.expires_at = floor(float(expires_at))
        except ValueError as err:
            if 'could not convert string to float' in str(err):
                self.expires_at = parse(expires_at).timestamp()
            else:
                raise
        except TypeError as err:
            self.expires_at = expires_at

        self._token_updater = token_updater or (lambda self,x: x)

        token = {}
        if access_token: token['access_token'] = access_token
        if refresh_token: token['refresh_token'] = refresh_token
        if expires_at: token['expires_at'] = self.expires_at

        self.refresh_lock = Lock()
        self.refresh_event = Event()

        self.session = OAuth2Session(client_id=self.client_id,
                                     auto_refresh_url='https://account.withings.com/oauth2/token',
                                     auto_refresh_kwargs={
                                         "action": "requesttoken",
                                         "client_id": self.client_id,
                                         "client_secret": self.client_secret,
                                     },
                                     token=token,
                                     redirect_uri=self.callback_url,
                                     scope='user.info,user.metrics,user.activity',
                                     token_updater=self._token_updater)


    def fetch_access_token(self, refresh=False):
        '''After this point, the contents of the response dict are saved in session
        as an oauthlib.OAuth2Token object.
        session.token accesses the object, while session.access_token gets just
        the string of latest access token.
        '''

        if not self.refresh_lock.acquire(blocking=False):
            print("WAITING ON ANOTHER THREAD TO REFRESH ACCESS TOKEN.")
            self.refresh_event.wait()
            return
        # self.refresh_event.clear()

        print("FETCHING ACCESS TICKET")

        try:
            fetch_token_url = 'https://account.withings.com/oauth2/token'

            if not refresh:
                print("FETCHING ACCESS TICKET")

                response = self.session.fetch_token(fetch_token_url,
                                                    include_client_id=True,
                                                    client_secret=self.client_secret,
                                                    code=self.auth_code,
                                                    action="requesttoken")

                # After this point, the contents of the response dict are saved in session
                # as an oauthlib.OAuth2Token object.
                # session.token accesses the object, while session.access_token gets just
                # the string of latest access token.

            else:
                print("REFRESHING ACCESS TICKET")
                response = self.session.refresh_token(fetch_token_url)

            # Call token_updater callback function to save off new creds
            if self._token_updater:
                print("Handling new creds with token_updater callback")
                self._token_updater(response)

            # Take in new auth details
            self.access_token = response['access_token']
            self.refresh_token = response['refresh_token']
            self.expires_at= floor(response['expires_at'])
            
            print("TOKEN AUTHENTICATED")

        except MissingTokenError as err:
            # Does this still happen?
            pprint("MissingTokenError raised.")
            print(err)
            raise

        finally:
            self.refresh_event.set()
            self.refresh_event.clear()
            self.refresh_lock.release()

        return response


    # TODO: implement backoff once proper exceptions are raised
    def _request(self, method, url, **kwargs):

        if not self.session.token:
            print("NO TOKEN YET")
            self.fetch_access_token()

        # if not self.expires_at:# and self.expires_at - datetime.now() < 0:
        if self.expires_at \
                and datetime.fromtimestamp(self.expires_at) < datetime.now():
            print("Withings API token has expired")
            self.fetch_access_token(refresh=True)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            withings_raise_for_status(response)

        # except oauthlib.oath2.TokenExpiredError as e:
        # except requests.exceptions.HTTPError as err:
        except AuthenticationFailedException as err:

            content = json.loads(response.content.decode('utf8'))

            if content['status'] == 401:
                if 'The access token provided' in content['error']:
                    self.fetch_access_token(refresh=True)
                    response = self.session.request(method, url, **kwargs)
                else:
                    raise

        return response


    get = partialmethod(_request, 'GET')
    post = partialmethod(_request, 'POST')



class Withings:
    # access_token is valid for three hours.
    # Use refresh_token to get a new access_token after it expires.


    def __init__(self, client_id, client_secret, callback_url,
                 auth_code=None, access_token=None,
                 refresh_token=None, expires_at=None,
                 token_updater_cb=None):

        self.client = WithingsOath2Client(client_id, client_secret, callback_url, 
                                          auth_code, access_token, 
                                          refresh_token, expires_at,
                                          token_updater_cb)


        # TODO: deprecate this
        self.headers = { "Authorization": "Bearer {}".format("HAH!") }#self.access_token) }


    def get_devices(self):
        """
        {'body': {'devices': [{'battery': 'high',
                       'deviceid': '...',
                       'hash_deviceid': '...',
                       'last_session_date': ...,
                       'model': 'Aura Sensor V2',
                       'model_id': 63,
                       'timezone': 'America/Chicago',
                       'type': 'Sleep Monitor'},
                      {'battery': 'medium',
                       'deviceid': '...',
                       'hash_deviceid': '...',
                       'last_session_date': ...,
                       'model': 'Body+',
                       'model_id': 5,
                       'timezone': 'America/Chicago',
                       'type': 'Scale'}]},
        'status': 0}
        """

        parms = { "action": "getdevice" }

        response = self.client.get('https://wbsapi.withings.net/v2/user',
                                   headers=self.headers,
                                   params=parms)

        results = response.json()

        if 'body' not in response and 'devices' not in results['body']:
            print('ERROR:','No body/devices in results.')
            pprint(response.text)
            return []

        return results['body']['devices']


    def get_measurements(self, type_name):
        """Fetches measurements.

        Parameters
        ----------
        type_name : str, int, MeasureType
            The string value, or integer code of the MeasureType, or
            even the MeasureType enum itself.
        """

        parms = { "action": "getmeas" }

        hdrs = self.headers

        if type_name:
            hdrs['type'] = str(MeasureType(type_name).code)

        response = self.client.get('https://wbsapi.withings.net/measure',
                                   headers=hdrs,
                                   params=parms)

        measurements = response.json()

        # Replace type-codes with type-names
        for record in measurements['body']['measuregrps']:
            for measure in record['measures']:
                measure['type'] = MeasureType(measure['type']).value
                # 'algo', 'fm', 'type', 'unit', 'value'

        return measurements['body']['measuregrps']


    def get_sleep_data(self, 
                       start_date=datetime(year=2019, month=5, day=16), 
                       end_date=datetime.now() + timedelta(days=1)):
        '''
        First viable startdate is default.
        Tomorrow is default enddate, to ensure latest night's data.
        If end_date > 24hrs after start_date, the API will instead use 24hrs after specified start_date.
        '''

        parms = {
            "action": "get",
            "startdate": start_date.strftime('%s'),
            "enddate": end_date.strftime('%s'),
            #"data_fields": 'hr,rr,snoring',
        }

        print('Fetching data between {} and {}'.format(start_date.date(), end_date.date()))

        response = self.client.get('https://wbsapi.withings.net/v2/sleep', params=parms)
        
        results = response.json()
        
        if 'body' not in results and 'series' not in results['body']:
            print('ERROR:','No body/series in results.')
            pprint(response.text)
            # '{"status":601,"body":{"wait_seconds":68},"error":"Too Many Requests"}'
            return []

        for sleep in results['body']['series']:
            sleep['state'] = SleepState(sleep['state']).value
        
        return results['body']['series']


    def get_sleep_detail_data(self, 
                       start_date=None, 
                       end_date=None,
                       last_update_date=None):
        '''
        If 'more'=True and 'offset'>0 in result['body'], then offset value is the 
        number of returned data from the current request, and there is more data available.
        Seems like this API returns MAX 300 records per request.
        '''

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

        response = self.client.get('https://wbsapi.withings.net/v2/sleep',
                                   headers=self.headers,
                                   params=parms)
        
        results = response.json()
        
        # if 'series' not in results['body']:
        #     print('ERROR:','No body/series in results.')
        #     pprint(response.text)
        #     return []

        return results['body']['series'], response.json()['body']['more']