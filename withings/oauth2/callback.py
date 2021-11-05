from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import threading
import urllib



class CallbackRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        # print("GET request\nPath: {}\nHeaders:\n{}".format(str(self.path), str(self.headers))) # log.INFO

        split_path = self.path.split('?')

        if len(split_path) != 2:
            raise Exception("No parameter query in HTTP call.")

        parsed_parms = urllib.parse.parse_qs(split_path[1])

        if not 'code' in parsed_parms:
            raise Exception("No 'code' field in query of HTTP call.")
        
        # if 'Content-Length' in self.headers:
        #     content_len = int(self.headers.get('Content-Length'))
        #     post_body = self.rfile.read(content_len)
        #     print('Post Body:') # log.INFO
        #     pprint(dict(urllib.parse.parse_qsl(post_body.decode()))) # log.INFO

        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        self.end_headers()

        # self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))
        self.wfile.write(json.dumps({ k:v[0] for k,v in parsed_parms.items() }).encode('utf-8'))

    def do_POST(self):

        logging.warning("SERVER POSTED TO KILL.")
        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        self.end_headers()

        self.wfile.write(json.dumps({"status":"killed"}).encode('utf-8'))



class Oath2CallbackServer(threading.Thread):
    def __init__(self, event=None, address='', port=8080):
        threading.Thread.__init__(self)
        self.event = event
        self.address=address
        self.port = int(port)

    def run(self):
        logging.debug("Starting httpd...\n") # log.INFO

        server_address = (self.address, self.port)
        httpd = HTTPServer(server_address, CallbackRequestHandler)

        if self.event: self.event.set()

        try:
            # handles incoming request once
            httpd.handle_request()
            logging.debug("REQUEST HANDLED") # log.INFO
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
            logging.debug("Stopping httpd...\n") # log.INFO



@contextmanager
def local_callback_server(callback_url):

    import requests
    import threading

    # Grab the port of the callback_url
    # server_address = re.split(r'(.+):(.+)[/]', callback_url)
    # port = server_address[2]

    logging.debug('Start callback server') # log.INFO

    evt = threading.Event()
    callback_handler = Oath2CallbackServer(evt)#, port=port)
    callback_handler.start()
    # Wait until the server is loaded up before kicking off the callback api
    evt.wait()
    
    try:
        yield
    except:
        # Tell the Oath2CallbackServer to quit.
        requests.post(callback_url)
        raise
    finally:
        callback_handler.join()