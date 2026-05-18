#!python

"""
Basic CherryPy Windows service for QATrack+...cobbled together
from various places online.

Requires Mark Hammond's pywin32 package.

"""

import os
import shutil
import sys
import sysconfig

import cherrypy
import win32service
import win32serviceutil

from qatrack import wsgi

DEPLOY_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
VENV_DIRECTORY = os.environ.get("VIRTUAL_ENV", os.path.join(DEPLOY_DIRECTORY, ".venv"))
PORT = 8080

logs_dir = os.path.join(DEPLOY_DIRECTORY, "logs")
if not os.path.isdir(logs_dir):
    os.makedirs(logs_dir, exist_ok=True)

ERROR_LOG = os.path.join(logs_dir, "cherry_py_err.log")
STD_ERR = os.path.join(logs_dir, "std_err.log")
STD_OUT = os.path.join(logs_dir, "std_out.log")
sys.stdout = open(STD_OUT, "a")
sys.stderr = open(STD_ERR, "a")
os.environ["VIRTUAL_ENV"] = VENV_DIRECTORY
sys.path.append(VENV_DIRECTORY)
sys.path.append(os.path.join(VENV_DIRECTORY, "Scripts"))


def setup():
    import glob

    if not glob.glob(os.path.join("C:/Windows/System32/pywintypes*dll")):
        import pywin32_postinstall

        lib_dir = sysconfig.get_path("platlib")
        pywin32_postinstall.install(lib_dir)

    platlib = sysconfig.get_path("platlib")
    orig_path = os.path.join(platlib, "win32", "pythonservice.exe")
    venv = os.environ.get("VIRTUAL_ENV")
    new_path = os.path.join(venv, "Scripts", "pythonservice.exe")

    if venv and not os.path.exists(new_path):
        shutil.copy(orig_path, new_path)


class QATrackService(win32serviceutil.ServiceFramework):
    """NT Service."""

    _svc_name_ = "QATrackCherryPyService"

    _svc_display_name_ = "QATrack CherryPy Service"

    _exe_name_ = os.path.join(os.environ.get("VIRTUAL_ENV", VENV_DIRECTORY), "Scripts", "pythonservice.exe")

    def SvcDoRun(self):
        sys.path.append(DEPLOY_DIRECTORY)
        os.environ["DJANGO_SETTINGS_MODULE"] = "qatrack.settings"
        os.chdir(DEPLOY_DIRECTORY)

        cherrypy.tree.graft(wsgi.application)

        cherrypy.config.update(
            {
                "global": {
                    "log.error_file": ERROR_LOG,
                    "log.screen": False,
                    "tools.log_tracebacks.on": True,
                    "engine.autoreload.on": False,
                    "engine.SIGHUP": None,
                    "engine.SIGTERM": None,
                    "server.socket_port": PORT,
                }
            }
        )

        cherrypy.engine.start()
        cherrypy.engine.block()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        cherrypy.engine.exit()

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # Run CherryPy directly in console/interactive mode
        sys.path.append(DEPLOY_DIRECTORY)
        os.environ["DJANGO_SETTINGS_MODULE"] = "qatrack.settings"
        os.chdir(DEPLOY_DIRECTORY)

        cherrypy.tree.graft(wsgi.application)

        cherrypy.config.update(
            {
                "global": {
                    "log.error_file": ERROR_LOG,
                    "log.screen": True,
                    "tools.log_tracebacks.on": True,
                    "engine.autoreload.on": False,
                    "server.socket_port": PORT,
                }
            }
        )

        cherrypy.engine.start()
        cherrypy.engine.block()
    else:
        setup()
        win32serviceutil.HandleCommandLine(QATrackService)
