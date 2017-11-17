#!python

"""

Basic CherryPy Windows service for QATrack+...cobbled together
from various places online.

Requires Mark Hammond's pywin32 package.

"""

import cherrypy
import win32serviceutil
import win32service
import win32event

import sys
import os

from qatrack import wsgi

DEPLOY_DIRECTORY = "C:/home/code/qatrackplus/"
ERROR_LOG = os.path.join(DEPLOY_DIRECTORY,"logs","cherry_py_err.log")
STD_ERR = os.path.join(DEPLOY_DIRECTORY,"logs","std_err.log")
STD_OUT = os.path.join(DEPLOY_DIRECTORY,"logs","std_out.log")
sys.stdout = open(STD_OUT,'a')
sys.stderr = open(STD_ERR,'a')

class QATrack030Service(win32serviceutil.ServiceFramework):

    """NT Service."""

    _svc_name_ = "QATrack030CherryPyService"

    _svc_display_name_ = "QATrack 030 CherryPy Service"

    def SvcDoRun(self):

        sys.path.append(DEPLOY_DIRECTORY)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'qatrack.settings'
        os.chdir(DEPLOY_DIRECTORY)

        cherrypy.tree.graft(wsgi.application)

        cherrypy.config.update({
            'global':{
                'log.error_file':ERROR_LOG,
                'log.screen': False,
                'tools.log_tracebacks.on':True,
                'engine.autoreload.on': False,
                'engine.SIGHUP': None,
                'engine.SIGTERM': None,
                'server.socket_port': 8030,
                }
            })

        cherrypy.engine.start()
        cherrypy.engine.block()

    def SvcStop(self):

        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        cherrypy.engine.exit()

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        # very important for use with py2exe
        # otherwise the Service Controller never knows that it is stopped !

if __name__ == '__main__':

    win32serviceutil.HandleCommandLine(QATrack030Service)
