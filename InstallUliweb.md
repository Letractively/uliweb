# Requirement #

  * Python 2.5+ (not support Py3K yet)
  * setuptools 0.6c11

# Extra Requirement #

  * SQLAlchemy 0.6+ (If you want to use Uliweb ORM you should install it. Recommend 0.6.7, I have not tested in 0.7b yet.)
  * pytz (Used in uliweb.utils.date and ORM for timezone process, but I think it's slow enough.)

# Installation #

  * easy\_install Uliweb
  * Download Uliweb package from http://code.google.com/p/uliweb/downloads/list or get the source files from svn:
```
       svn checkout http://uliweb.googlecode.com/svn/trunk/ uliweb
```
  * In uliweb installation directory, run `setup.py` to install it:
```
       python setup.py develop
       or
       python setup.py install
```

> The first command will install a link of the current Uliweb directory to the Python site-packages directory. , and you can find an entry in easy\_install.pth. So this style will let you upgrade new version very simplely just through update the uliweb source code, and you don't need to reinstall it again when you updated the source code from svn.

> These command will also install a script named `uliweb` to Python/Scripts  directory. Make sure that you have added the Python and Python/Scripts directories to your systems search path(adding the new path to the PATH environment). Doing this allows you to run the uliweb scripts anywhere on te commandline.
  * After above steps, run `uliweb` command in command line and see the tutorials to learn how to use `uliweb` for web application development.