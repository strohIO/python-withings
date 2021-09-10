
import json
from pprint import pprint
import sys
import requests
# from requests.models import Response

from .status_codes import codes as withings_codes


class StatusException(Exception):
    def __init__(self, status_code, error, *args, **kwargs):
        message = '({}) {}'.format(status_code, error)
        super().__init__(message, 
        *args, **kwargs)


class AuthenticationFailedException(StatusException):
    '''Withings response status exception'''

class InvalidParamsException(StatusException):
    '''Withings response status exception'''
# from oauthlib.oauth2.rfc6749.errors import InvalidRequestFatalError # description, uri, state, status_code, request

class UnauthorizedException(StatusException):
    '''Withings response status exception'''
# from oauthlib.oauth2.rfc6749.errors import UnauthorizedClientError # description, uri, state, status_code, request

class ErrorOccurredException(StatusException):
    '''Withings response status exception'''

class TimeoutException(Exception):
    '''Withings response status exception'''
# from requests.exceptions import Timeout #(response (optional), request(even more optional, as it will attempt to take a request out of an included response.))

class BadStateException(StatusException):
    '''Withings response status exception'''

class TooManyRequestsException(StatusException):
    '''Withings response status exception'''
# from werkzeug.exceptions import TooManyRequests(description=None, response=None, retry_after=None)

class NotImplementedException(Exception):
    '''Withings response status exception'''
# NotImplementedError




# raise_for_status, raise_from_error, detect_and_raise_error, raise_exceptions
def raise_for_status(response):

    from functools import partial
    
    if isinstance(response, dict) and \
            'status' in response:
        status = response['status']
    elif isinstance(response, requests.models.Response):
        # requests.raise_for_status here first?

        try:
            response = json.loads(response.content.decode('utf8'))
            # pprint(response)
            status = response['status']
        except ValueError:
            print("Returned content isn't JSON format.")
            pprint(response.__dict__)
            raise
    else:
        status = int(response.status_code)


    # if status_code in withings_codes.operation_was_successful:
    #     pass

    if status in withings_codes.authentication_failed:
        # {"status":401,"body":{},"error":"XRequestID: Not provided invalid_token: The access token provided is invalid"}
        raise AuthenticationFailedException(status, response['error'])

    elif status in withings_codes.invalid_params:
        raise InvalidParamsException(status, response['error'])
    elif status in withings_codes.unauthorized:
        raise UnauthorizedException(status, response['error'])
    elif status in withings_codes.an_error_occurred:
        raise ErrorOccurredException(status, response['error'])
    elif status in withings_codes.timeout:
        raise TimeoutException(status, response['error'])
    elif status in withings_codes.bad_state:
        raise BadStateException(status, response['error'])
    elif status in withings_codes.too_many_request:
        raise TooManyRequestsException(status, response['error'])
    elif status in withings_codes.not_implemented:
        raise NotImplementedException(status, response['error'])
    
    else:
        pass




if __name__ == "__main__":
    class Resp:
        status_code = "305"

    raise_for_status(Resp)