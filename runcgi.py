#!/usr/bin/env python
#coding=utf-8

"""
Run uliweb with cgi / scgi / fastcgi!
"""

import os
import sys
import manage


HELP_TEXT = r"""
Run uliweb with cgi scgi fastcgi.
flup need,http://trac.saddi.com/flup

protocol=cgi,scgi,fcgi(default:cgi)
host=HOSTNAME example:127.0.0.1
port=PORT example:3033
socket=SCKET_FILE_NAME  UNIX Socet example:/tmp/uliweb.sock
method=prefork/threaded default:threaded
daemonize=true/false  default:false
pidfile=FILENAME  PID file
outfile=FILENAME  stdout
errfile=FILENAME  stderr
worldir=default:/
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
    'daemoize':None,
    'workdir':'/',
    'pidfile':None,
    'outfile':None,
    'errfile':None,
    }


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
    pidfile = options.get('pidfile',None)
    if pidfile:
        open(pidfile,'w').write('%d\n' % os.getpid())
    application = manage.make_application()
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
