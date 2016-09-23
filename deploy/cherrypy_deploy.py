#!python
from qatrack import wsgi
from cherrypy import wsgiserver
server = wsgiserver.CherryPyWSGIServer(
    ('127.0.0.1', 8080), wsgi.application
)
server.start()
