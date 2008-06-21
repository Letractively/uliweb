#!/usr/bin/env python
#coding=utf-8

"""
以cgi scgi fastcgi方式运行uliweb！
"""

import os
import sys
import manage


HELP_TEXT = r"""
以cgi scgi fastcgi方式运行uliweb.
flup模块是必需的。http://trac.saddi.com/flup

protocol=协议  cgi,scgi,fcgi(默认cgi)
host=监听地址   例：127.0.0.1
port=端口号  例：3033
socket=文件名  UNIX Socet方式监听 例:/tmp/uliweb.sock
method=prefork/threaded 默认为threaded
daemonize=true/false  默认为false
pidfile=文件名  PID文件
outfile=文件名  stdout
errfile=文件名  stderr
worldir=/ 工作目录 默认
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
    if application.config.DEBUG:
        from werkzeug.debug import DebuggedApplication
        application = DebuggedApplication(application)
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
