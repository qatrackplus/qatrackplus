import os

import cherrypy
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qatrack.settings')

application = get_wsgi_application()

if __name__ == '__main__':
    cherrypy.config.update({
        'server.socket_host': '127.0.0.1', # Use 0.0.0.0 if not running behind IIS/Nginx
        'server.socket_port': 8080,
        'engine.autoreload.on': False,
        'log.screen': True
    })
    
    cherrypy.tree.graft(application, '/')
    cherrypy.engine.start()
    cherrypy.engine.block()