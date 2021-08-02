
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys
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

        print("SERVER POSTED TO KILL.")
        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        self.end_headers()

        self.wfile.write(json.dumps({"status":"killed"}).encode('utf-8'))



class Oath2CallbackServer(threading.Thread):
    def __init__(self, event=None, port=8080):
        threading.Thread.__init__(self)
        self.event = event
        self.port = port

    def run(self):
        print("Starting httpd...\n") # log.INFO

        server_address = ('', self.port)
        httpd = HTTPServer(server_address, CallbackRequestHandler)

        if self.event: self.event.set()

        try:
            # handles incoming request once
            httpd.handle_request()
            print("REQUEST HANDLED") # log.INFO
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
            print("Stopping httpd...\n") # log.INFO




if __name__ == "__main__":

    # mutex = threading.Lock()
    evt = threading.Event()

    # ocs = Oath2CallbackServer(mutex)
    ocs = Oath2CallbackServer(evt)
    ocs.start()
    
    # Wait until CallbackServer has been hit and handles the request
    evt.wait()

    print("Authorization started.")

    ocs.join()
    print("Authorization complete.")


    # To test with:
    # $ python -m withings.oath2 &
    # $ wget -q -O - 'http://localhost:8080?code=WAP'