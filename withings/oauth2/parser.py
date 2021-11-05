
from html.parser import HTMLParser
import re


class CSRFParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.secret = None
    
    def handle_starttag(self, tag, attrs):
        '''Looking for {"name":"csrf_token", "type":"hidden", "value": "####"}'''
        if tag == "input":
            secrets = dict(attrs)
            if 'name' in secrets and secrets['name'] == 'csrf_token':
                self.secret = secrets['value']

    def get_secret(self):
        return self.secret


class UserParser(HTMLParser):

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.check_data = False
        self.user_id = None
        self.url_query = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            a = dict(attrs)
            if 'href' in a and 'selecteduser' in a['href']:
                self.url_query = a['href']
                self.check_data = True

    def handle_data(self, data):
        if self.check_data:
            if data == self.username:
                self.user_id = re.search(r'selecteduser=(\d+)', self.url_query).groups()[0]
            self.check_data = False

    def get_user_id(self):
        return self.user_id