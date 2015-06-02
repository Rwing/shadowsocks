#encoding=utf-8

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import io,shutil  
import urllib,time
import getopt,string
import json
import logging
from threading import Thread
from shadowsocks import shell, daemon, eventloop, tcprelay, udprelay, asyncdns

class HttpApiThread(Thread):
	def __init__(self, loop, dns_resolver):
		super(HttpApiThread, self).__init__()
		self.loop = loop
		self.config = shell.get_config(False)
		self.dns_resolver = dns_resolver
		self.tcp_servers_pool = {}
		self.udp_servers_pool = {}

	def run(self):
		try:
			server = MyServer(('127.0.0.1', 8000), MyRequestHandler)
			print 'started httpserver...'
			server.serve_forever(self)
		except KeyboardInterrupt:
			server.socket.close()

		pass

class MyServer(HTTPServer):
    def serve_forever(self, myServer):
        self.RequestHandlerClass.myServer = myServer 
        HTTPServer.serve_forever(self)

class MyRequestHandler(BaseHTTPRequestHandler):
	myServer = None

	def do_GET(self):
		content =""
		if '?' in self.path:
			query = urllib.splitquery(self.path)
			action = query[0] 
					 
			if query[1]:
				queryParams = {}
				for qp in query[1].split('&'):
					kv = qp.split('=')
					queryParams[kv[0]] = urllib.unquote(kv[1]).decode("utf-8", 'ignore')
					content+= kv[0]+':'+queryParams[kv[0]]+"\r\n"

			#example
			#http://127.0.0.1:8000/?action=start&port=8080&password=xxxxxx
			if queryParams['action'] == 'start':
				port = int(queryParams['port'])
				a_config = self.myServer.config.copy()
				a_config['server_port'] = port
				a_config['password'] = queryParams['password']
				tcp_server = tcprelay.TCPRelay(a_config, self.myServer.dns_resolver, False)
				tcp_server.add_to_loop(self.myServer.loop)
				self.myServer.tcp_servers_pool[port] = tcp_server

			#example
			#http://127.0.0.1:8000/?action=stop&port=8080&password=xxxxxx
			elif queryParams['action'] == 'stop':
				port = int(queryParams['port'])
				tcp_server = self.myServer.tcp_servers_pool[port]
				del self.myServer.tcp_servers_pool[port]
				tcp_server.destroy()

			enc="UTF-8"  
			content = content.encode(enc)          
			f = io.BytesIO()  
			f.write(content)  
			f.seek(0)  
			self.send_response(200)  
			self.send_header("Content-type", "text/html; charset=%s" % enc)  
			self.send_header("Content-Length", str(len(content)))  
			self.end_headers()  
			shutil.copyfileobj(f,self.wfile)   


if __name__=='__main__':

	thread = HttpApiThread()
	thread.start()
	print('do main')