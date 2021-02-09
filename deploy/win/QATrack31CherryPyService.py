#!python

"""

Basic CherryPy Windows service for QATrack+...cobbled together
from various places online.

Requires Mark Hammond's pywin32 package.

"""

import distutils.sysconfig
import glob
import os
import shutil
import sys

import cherrypy
from qatrack import wsgi
import win32service
import win32serviceutil

VENV_DIRECTORY = "C:/deploy/venvs/qatrack31/"
DEPLOY_DIRECTORY = "C:/deploy/qatrackplus/"
PORT = 8080


ERROR_LOG = os.path.join(DEPLOY_DIRECTORY, "logs", "cherry_py_err.log")
STD_ERR = os.path.join(DEPLOY_DIRECTORY, "logs", "std_err.log")
STD_OUT = os.path.join(DEPLOY_DIRECTORY, "logs", "std_out.log")
sys.stdout = open(STD_OUT, 'a')
sys.stderr = open(STD_ERR, 'a')
os.environ["VIRTUAL_ENV"] = VENV_DIRECTORY
sys.path.append(VENV_DIRECTORY)
sys.path.append(os.path.join(VENV_DIRECTORY, "Scripts"))


def setup():

    if not glob.glob(os.path.join("C:/Windows/System32/pywintypes*dll")):
        import pywin32_postinstall
        lib_dir = distutils.sysconfig.get_python_lib(plat_specific=1)
        pywin32_postinstall.install(lib_dir)

    sitepackages = distutils.sysconfig.get_python_lib()
    orig_path = os.path.join(sitepackages, "win32", "pythonservice.exe")
    venv = os.environ.get("VIRTUAL_ENV")
    new_path = os.path.join(venv, "Scripts", "pythonservice.exe")

    if venv and not os.path.exists(new_path):
        shutil.copy(orig_path, new_path)


class QATrack030Service(win32serviceutil.ServiceFramework):

    """NT Service."""

    _svc_name_ = "QATrack031CherryPyService"

    _svc_display_name_ = "QATrack 031 CherryPy Service"

    _exe_name_ = os.path.join(os.environ['VIRTUAL_ENV'], 'Scripts', 'pythonservice.exe')

    def SvcDoRun(self):

        sys.path.append(DEPLOY_DIRECTORY)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'qatrack.settings'
        os.chdir(DEPLOY_DIRECTORY)

        cherrypy.tree.graft(wsgi.application)

        cherrypy.config.update({
            'global': {
                'log.error_file': ERROR_LOG,
                'log.screen': False,
                'tools.log_tracebacks.on': True,
                'engine.autoreload.on': False,
                'engine.SIGHUP': None,
                'engine.SIGTERM': None,
                'server.socket_port': PORT,
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

    setup()
    win32serviceutil.HandleCommandLine(QATrack030Service)
