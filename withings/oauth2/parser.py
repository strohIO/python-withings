
from html.parser import HTMLParser



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