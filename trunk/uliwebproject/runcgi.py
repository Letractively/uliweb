#!/usr/bin/env python
#coding=utf-8

"""
Run uliweb with cgi / scgi / fastcgi!
"""

import os
import sys
from uliweb import manage


HELP_TEXT = r"""
Run uliweb with cgi scgi fastcgi.
flup need,http://trac.saddi.com/flup

protocol=cgi,scgi,fcgi(default:cgi)  If cgi , can't use other parameters.
host=HOSTNAME example:127.0.0.1
port=PORT example:3033


==========

Can use in linux only:

socket=SCKET_FILE_NAME  UNIX Socet example:/tmp/uliweb.sock
method=prefork/threaded default:threaded
daemonize=true/false  default:false
pidfile=FILENAME  PID file
outfile=FILENAME  stdout
errfile=FILENAME  stderr
worldir=default:  ./
Examples:

CGI:
runcgi.py


SCGI:
runcgi.py protocol=scgi socket=/tmp/uliweb.sock method=threaded
runcgi.py protocol=scgi port=3033
...

FastCGI:
runcgi.py protocol=fcgi socket=/tmp/uliweb.sock method=profork
...

"""


CGI_OPTIONS = {
    'protocol':'cgi',
    'host':None,
    'port':None,
    'socket':None,
    'method':'fork',
    'daemoinze':None,
    'workdir':'.',
    'pidfile':None,
    'outfile':None,
    'errfile':None,
    }

path = os.path.dirname(__file__)
if path not in sys.path:
    sys.path.insert(0, path)
apps_dir = os.path.join(path, 'apps')

def run(args=[],**kwargs):
    options = CGI_OPTIONS.copy()
    options.update(kwargs)
    for arg in args:
        if '=' in arg:
            k,v = arg.split('=',1)
            options[k.lower()] = v
        else:
            options[arg.lower()] = True

    if 'help' in options:
        print HELP_TEXT
        return True

    modname = 'flup.server.' + options['protocol']
    if options['method'] == 'prefork':
        modname = modname + '_fork'
    try:
        WSGIServer = __import__(modname,fromlist=modname).WSGIServer
    except:
        print 'Can not import module',modname
        return False

    if os.name == 'posix' and options.get('daemonize','false') == 'true' and options['protocol'] != 'cgi':
        if os.fork():
            os._exit(0)
        os.setsid()
        os.chdir(options.get('workdir','.'))
        if os.fork():
            os._exit(0)
        os.umask(077)
        nofile = open('/dev/null',os.O_RDWR)
        errfile = open(options.get('errfile','/dev/null'),'a+',0)
        outfile = open(options.get('outfile','/dev/null'),'a+',0)
        os.dup2(nofile.fileno(),sys.stdin.fileno())
        os.dup2(errfile.fileno(),sys.stderr.fileno())
        os.dup2(outfile.fileno(),sys.stdout.fileno())
        sys.stdout = outfile
        sys.stderr = errfile

    pidfile = options.get('pidfile',None)
    if pidfile:
        open(pidfile,'w').write('%d\n' % os.getpid())
    application = manage.make_application(apps_dir=apps_dir)
    if options['protocol'] == 'cgi':
        os.environ['SCRIPT_NAME'] = ''
        WSGIServer(application).run()
    else:
        if options['socket']:
            bindAddress = options['socket']
        elif options['port']:
            bindAddress = (options['host'] or '127.0.0.1',int(options['port']))
        else:
            bindAddress = None
        WSGIServer(application,environ={'SCRIPT_NAME':''},bindAddress=bindAddress).run()


if __name__ == '__main__':
    run(sys.argv)
