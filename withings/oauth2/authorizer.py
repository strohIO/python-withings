
import requests
import threading
import urllib

from .callback import Oath2CallbackServer
from .parser import CSRFParser



def get_url_params(url_path):
    split_path = url_path.split('?')

    if len(split_path) != 2:
            raise Exception("No parameter query in url.")

    parsed_parms = urllib.parse.parse_qs(split_path[1])

    return { k:v[0] for k,v in parsed_parms.items() }



class WithingsAUTH:

    def __init__(self, client_id, callback_url):

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
            'state': "HAHAHA",
            # Scale - user.metrics
            # Sleep - user.activity
            'scope': 'user.info,user.metrics,user.activity',
            'redirect_uri': callback_url, #redirect_uri,
            'b': 'authorize2',
        }


    def _call(self, verb: str, route: str, data=None, **kwargs):

        if data:
            payload = urllib.parse.urlencode(data)
        
        response = self._session.request(method=verb,
                                         url="https://account.withings.com/oauth2_user/{}".format(route),
                                         params=urllib.parse.urlencode(self.parms),
                                         headers=self.headers,
                                         data=data,
                                         **kwargs)

        return response


    def _get_csrf_token(self, **kwargs):

        response = self._call('get', 'account_login', **kwargs)

        # if routed response comes up with 'selecteduser' param, save value
        if 'selecteduser' in response.url:
            query = get_url_params(response.url)
            self.parms['selecteduser'] = query['selecteduser']
            print('selecteduser acquired.')

        # Extract csrf_token value from html element
        parser = CSRFParser()
        parser.feed(response.text)
        csrf_token = parser.get_secret()

        if not csrf_token:
            pprint(response.text)
            raise Exception("No CSRF Token element found on HTML page.")

        print('CSRF_TOKEN acquired.')

        return csrf_token


    def _sign_in(self, csrf_token: str, user_email, password):
        
        body = {
            'email': user_email,
            'password': password,
            'is_admin': 'f',
            'csrf_token': csrf_token,
        }

        response = self._call("post", "account_login", data=body)

        # check response.status_code for failed logins
        if 'session_key' not in self._session.cookies:
            print(response.url)
            raise Exception("""Sign-in error: no session_key provided. 
                Was there already too many failed attempts?""")

        print('SESSION_KEY Cookie acquired')

        return self._session.cookies['session_key']


    def _authorize(self, csrf_token):

        body = {
            'authorized': 1,
            'csrf_token': csrf_token,
        }

        response = self._call("post", "authorize2", body)

        try:
            result = response.json()
        except json.decoder.JSONDecodeError as e:
            print(response.text)
            raise

        print('Authorization Code acquired')

        return result['code']
        #except (ConnectionResetError, ProtocolError, requests.exceptions.ConnectionError):


    def authorize(self, user_email, password):

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
        try:
            code = self._authorize(new_csrf_token)
        except:
            # Tell the CallbackServer to quit.
            requests.post(self.callback_url)
            raise

        # Ensure server finishes before proceeding
        callback_handler.join()
        print("Authorization complete.") # log.INFO

        # This authorization code is passed to the API to get the access token & refresh token.
        return code
