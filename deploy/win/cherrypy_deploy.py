#!python
from cheroot.wsgi import Server as WSGIServer

from qatrack import wsgi

server = WSGIServer(('127.0.0.1', 8030), wsgi.application)
server.start()
