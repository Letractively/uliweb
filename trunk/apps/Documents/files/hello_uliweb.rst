Hello, Uliweb
================

:Author: Limodou <limodou@gmail.com>
:Translator: E.T <iwinux@gmail.com>

.. contents:: 

This tutorial will show you around the Uliweb frameworks. 
In the following simple demo, we're going to generate a plain page 
which displays "Hello, Uliweb." step by step.

Getting Started
-----------------

The first thing you should do is:

a) get the latest version of Uliweb from http://code.google.com/p/uliweb

or

b) check it out from svn.

::

    svn co http://uliweb.googlecode.com/svn/trunk/ uliweb

and then place it in a directory.

Note: Uliweb contains the source code of the website (uliwebproject) 
which is in 'apps/', however, we don't need it in this tutorial. 
You can delete it directly or modify the file named 'settings.py' in 'apps/' 
to make our new app the only enabled one. And the third way is to create
a new working directory, so the environment is pure, and we choose the third way.

Creating new project
---------------------

Uliweb has already provided a command line tool named manage.py, you can use
it to execute some commands. Enter the installed directory of Uliweb, and swith 
to command line, then execute:

::

    python manage.py export ../uliweb_work
    
Behind export is a directory name, I'll create a new directory named uliweb_work
and it'll exist in the same level with uliweb, and you can of cause change it to
any directory you want.

If the command execution is successful, it'll output nothing. Then goto to the new
build directory. This directory is a complete uliweb copy, but there is no any 
APP, so it's a pure working environment.


Creating 'Hello' app
----------------------

Uliweb provides us with a command-line tool called 'manage.py' 
to perform some operations. Now we create a brand new Hello app first.

.. code::

    python manage.py makeapp Hello
    
Note: manage.py is in the installed directory of Uliweb.

After the command above is executed successfully, 
you can find the following things in 'apps/'::

    apps/
      __init__.py
      settings.py
      Hello/
        __init__.py
        settings.py
        views.py
        static/
        templates/
        
Well, the Hello app has been created now, so the next step is to generate 
the message "Hello, Uliweb".

Displaying "Hello, Uliweb"
----------------------------

Open Hello/view.py, you will see:

.. code:: python

    #coding=utf-8
    from uliweb.core.SimpleFrame import expose
    
    @expose('/')
    def index():
        return '<h1>Hello, Uliweb</h1>'

The above lines of code shown above was generated automatically when executing 'makeapp', 
and we even don't need write any code, there is already a Hello, Uliweb view function!

@expose('/') is used for URL Mapping, which means map the url '/' to 
the view function below. So when visiting http://localhost:8000/, function index() 
will be called. If a function without being decorated by expose, it will not 
be mapped to any url and is treated as a local function.

Note that we haven't define any arguments for index(), and we haven't define any 
in expose either. When defining arguments, they should be the same in index() and expose.

Then the function returns a line of HTML code that will be displayed directly in browser.

Launch
--------

Well, let's run it to see the results.
Execute the following command:

.. code:: console

    python manage.py runserver
    
We have run the development server now, and then we can see the results 
by typing http://localhost:8000 in the browser.
Pretty easy, right? But that's not enough, let's make some changes instead: adding templates.


Adding templates
-------------------

If your view function returns a dict object, Uliweb will apply it to a template automatically.
The filename of a template is the same as your view function, ending with '.html', 
for example, the template of index() is 'index.html'. Templates are placed into 
the directory 'templates' which was created when creating a new app.
In order to avoid affecting the index() function, we add a new function.

.. code:: python

    @expose('/template')
    def template():
        return {}

Then create a new file 'template.html' in 'apps/Hello/templates' with contents shown below£º

.. code:: html

    <h1>Hello, Uliweb</h1>
    
Type http://localhost:8000/template in the browser, you will see the same thing as the previous one.

Using template variables
---------------------------

In the two examples shown above, all data was put directly, making the app less general, 
so we're going to use template variables to change that.
Add another view function with the following code:


.. code:: python

    @expose('/template1')
    def template1():
        return {'content':'Uliweb'}

Then create 'template1.html' in 'apps/Hello/templates' and type in this line:

.. code:: html

    <h1>Hello, {{=content}}</h1>
    
The function template1() returns a dict object with 'content' representing the content to be displayed. 
If you feel uncomfortable with the form '{}', try this alternative:

.. code:: python

    return dict(content='Uliweb')
    
or£º

.. code:: python

    content = 'Uliweb'
    return locals()
    
The first one uses dict() to construct a dict object while 
the second one uses the builtin function locals() directly - as long as you 
define the corresponding variables. Although locals() may return some irrelevant variables, 
it is not harmful.

.. note::

    Because the development server Uliweb provides has the ability to reload apps, 
    you don't need to restart the server too often when making changes - 
    refreshing you browser is enough in most situations. However, when 
    you are struck with templates cache or something goes wrong seriously, 
    you do need to restart it. Pressing Ctrl + C in command line can shutdown 
    the server, and then you can restart it.

End
------

This tutorial only demonstrates some fundamental things like view and templates 
and lots of topics are not mentioned, such as:

* Organizing Apps
* Using Database
* Configurations
* etc.

You can find other documentations on http://uliwebproject.appspot.com, 
and most import, Uliweb is getting powerful!
