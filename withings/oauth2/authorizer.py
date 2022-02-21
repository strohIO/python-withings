from json.decoder import JSONDecodeError
import logging
import re
import requests
import urllib

from .callback import local_callback_server
from ..exceptions import MismatchingRedirectURIError
from .parser import CSRFParser
from .parser import UserParser



def get_url_host(url_path):
    parsed_uri = urllib.parse.urlparse(url_path)
    host = parsed_uri.netloc
    return host


def get_url_params(url_path):
    split_path = url_path.split('?')

    if len(split_path) != 2:
            raise Exception("No parameter query in url.")

    parsed_parms = urllib.parse.parse_qs(split_path[1])

    return { k:v[0] for k,v in parsed_parms.items() }


# TODO: add exceptions from responses
# oauthlib.oauth2.rfc6749.errors
#   InvalidScopeError

class WithingsAUTH:

    def __init__(self, client_id, callback_url, state='ABCDEFG'):

        self._session = requests.Session()

        self.callback_url = callback_url
        # self.client_id = client_id

        self.headers = {
            'Host': 'account.withings.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        self.parms = {
            'response_type': 'code',
            'client_id': client_id,
            'state': state,
            # Scale - user.metrics
            # Sleep - user.activity
            'scope': 'user.info,user.metrics,user.activity',
            'redirect_uri': callback_url, #redirect_uri,
            'b': 'authorize2',
        }


    def _call(self, verb: str, route: str, data=None, **kwargs):

        if data:
            payload = urllib.parse.urlencode(data)

        response = self._session.request(
            method=verb,
            url="https://account.withings.com/oauth2_user/{}".format(route),
            params=urllib.parse.urlencode(self.parms),
            headers=self.headers,
            data=data,
            **kwargs)

        return response


    def _get_csrf_token(self, username=None, **kwargs):

        response = self._call('get', 'account_login', **kwargs)

        # Get ending route of url to check where we're at
        route = re.search(r'\/([\w_]+)\?', response.url).groups()[0]

        # if there are multiple users in this account, there will be a
        # select-user page interjected here. Use the provided username to
        # get the appropriate user_id value
        if route == 'user_select':
            user_parser = UserParser(username)
            user_parser.feed(response.text)
            user_id = user_parser.get_user_id()
            self.parms['selecteduser'] = user_id
            response = self._call('get', 'account_login')
            logging.debug('User {} selected'.format(username))

        # if routed response comes up with 'selecteduser' param, save value
        elif 'selecteduser' in response.url:
            query = get_url_params(response.url)
            self.parms['selecteduser'] = query['selecteduser']
            logging.debug('selecteduser acquired.')

        # Extract csrf_token value from html element
        parser = CSRFParser()
        parser.feed(response.text)
        csrf_token = parser.get_secret()

        if not csrf_token:
            resp = response.json()

            if 'redirect_uri_mismatch' in resp['errors'][0]['message']:
                raise MismatchingRedirectURIError(self.callback_url)
            else:
                logging.error(resp)
                raise Exception("No CSRF Token element found on HTML page.")

        logging.debug('CSRF_TOKEN acquired.')

        return csrf_token


    def _sign_in(self, csrf_token: str, account_email, account_password):
        
        body = {
            'email': account_email,
            'password': account_password,
            'is_admin': 'f',
            'csrf_token': csrf_token,
        }

        response = self._call("post", "account_login", data=body)

        # check response.status_code for failed logins
        if 'session_key' not in self._session.cookies:
            logging.debug(response.url)
            raise Exception("""Sign-in error: no session_key provided. 
                Was there already too many failed attempts?""")

        logging.debug('SESSION_KEY Cookie acquired')

        return self._session.cookies['session_key']


    def _authorize(self, csrf_token, **kwargs):
        """
        For API Keys and such, it's recommended to pass 'auth' into kwargs as a requests auth object,
        rather than replacing headers.
        """

        body = {
            'authorized': 1,
            'csrf_token': csrf_token,
        }

        # Interject updating headers in-between redirect to ensure proper headers are sent to callback server
        first_response = self._call("post", "authorize2", data=body, allow_redirects=False, **kwargs)
        redirect_request = first_response._next
        # Withings leaves this as their own 'account.withings.com', potentially breaking the redirect with AWS
        # redirect_request.headers['Host'] = '*.execute-api.*.amazonaws.com'
        redirect_request.headers['Host'] = get_url_host(self.callback_url)

        response = self._session.send(redirect_request)

        try:
            if response.status_code == 403:
                from pprint import pprint
                pprint(response.__dict__)
                raise Exception('403 Response Status')
            else:
                result = response.json()
                code = result['code']
        except JSONDecodeError as e:
            logging.error(response.text)
            raise

        logging.debug('Authorization Code acquired: {}'.format(response.json()))

        return code
        #except (ConnectionResetError, ProtocolError, requests.exceptions.ConnectionError):


    def authorize(self, account_email, account_password, username=None, callback_server_gen=local_callback_server, **kwargs):
        '''username may not be necessary, if there is only a single user in the account.'''

        # GET:  grab csrf_token from a hidden element in the html on the ACCOUNT_LOGIN page
        csrf_token = self._get_csrf_token()

        # POST: attach that csrf to body along with creds to post to basically that same URL
        self._sign_in(csrf_token, account_email, account_password)

        logging.debug("SESSION KEY: {}".format(self._session.cookies['session_key']))

        # GET: grab new csrf_token, but with the session_id cookie included from the previous call
        #       to be taken to the 'Allow this app?' page
        # Also grabs the selecteduser ID
        new_csrf_token = self._get_csrf_token(username)

        with callback_server_gen(self.callback_url):
            # Request Authorization Code. Pulls from own server after redirect.
            # Posts to the AUTHORIZE2 page, which forwards to the encompassing CallbackServer, with a 'code' query 
            # parameter, which the CallbackServer reads and returns back to this authorize response.
            code = self._authorize(new_csrf_token, **kwargs)

        logging.debug("Authorization complete.") # log.INFO

        # This authorization code is passed to the API to get the access token & refresh token.
        return code
