Deployment Guide
===================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

GAE(Google Application Engine)
--------------------------------

GAE is a web running environment provided by Google, you should require an account
before you can use it. Then use this account to create your project. 

You should test your project code under GAE SDK development environment first.

#. Using ``export`` command export Uliweb to your project directory. You should name
   your project directory as the same as the application name your created in
   GAE. Say your project name is ``myproject``, and you install GAE SDK in 
   ``C:\Program Files\Google\google_appengine``, so you can use the command:

   ::

        python manage.py export "C:\Program Files\Google\google_appengine\myproject"
        
   I used ``-n`` option above, because you can't use Uliorm(Uliweb ORM module) 
   on GAE now, so let's don't export it. You should notice that the target
   directory is quoted by double-quotors, that's because there is space character
   in the directory. So when you finish it, the development directory is ready.

#. Modify ``app.yaml`` file, change the value of ``application`` to your project name, 
   for example: ``myproject``.
#. Then you can begin your web development. You can use Uliweb development server
   first, then switch to GAE development server to test your project.
#. Upload your project with ``appcfg.py`` tool:

   ::

        python appcfg.py update myproject
        
Apache
---------

mod_wsgi
~~~~~~~~~~~

#. You should refer `mod_wsgi <http://code.google.com/p/modwsgi/>`_ document, and 
   install mod_wsgi.so to apache.

   * Just copy mod_wsgi.so to apache/modules directory.

   In windows you can see:

        http://code.google.com/p/modwsgi/wiki/InstallationOnWindows

   In Linux you can see:

        http://code.google.com/p/modwsgi/wiki/InstallationOnLinux


#. Modify apache's httpd.conf file

   * Add below code

     ::
    
        LoadModule wsgi_module modules/mod_wsgi.so
        WSGIScriptAlias / /path/to/uliweb/wsgi_handler.wsgi
        
        <Directory /path/to/youruliwebproject>
        Order deny,allow
        Allow from all
        </Directory>
        
     Above assume the root URL is ``/``, you should change it as you want, for 
     example ``/myproj``.
    
     Here is an example, it runs on windows platform:
    
     ::
    
        WSGIScriptAlias / d:/project/svn/uliweb/wsgi_handler.wsgi
        
        <Directory d:/project/svn/uliweb>
        Order deny,allow
        Allow from all
        </Directory>

#. Restart apache
#. Test it. Startup browser, and enter the URL http://localhost/YOURURL to test
   whether the visit is right.

Static files
---------------

For now, Uliweb can serve static files already, but you may want to use apache
for serving static files. You can use exportstatic command to collect all static
files from all available apps to target directory, then configure target static
directory in the web server configure file.
 
    
