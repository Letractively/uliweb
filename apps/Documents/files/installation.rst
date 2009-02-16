Installation
=================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

Requirement
--------------

* setuptools (recommend 0.6c9+)

Installation
---------------

#. Download Uliweb package from http://code.google.com/p/uliweb/downloads/list or
   get the source files from svn::

       svn checkout http://uliweb.googlecode.com/svn/trunk/ uliweb

#. In uliweb installation directory, run ``setup.py`` to install it::

       python setup.py develop
    
   This command will install a link of current Uliweb directory to Python 
   site-packages directory, and you can find an entry in easy_install.pth.
   And this command will also install a script named ``uliweb`` to Python/Scripts
   directory. So if you've already set the Python/Scripts to search path, you 
   can directly run it from command line. If not, please add Python and Python/Scripts
   directories to search path(change PATH environment to add new path).
    
   .. note::
    
       Why not use ``python setup.py install``? Because I saw that the ``uliweb`` script
       can't be installed correctly, I don't know why.
    
#. After above steps, you should already run ``uliweb`` command in command line. 
   Next you should see some tutorials to learn how to use ``uliweb`` command and how
   to develop a web site with Uliweb.