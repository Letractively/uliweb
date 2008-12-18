Hello, Uliweb
================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

This tutorial will show you around the Uliweb frameworks. 
In the following simple demo, we're going to generate a plain page 
which displays "Hello, Uliweb." step by step.

Getting Started
-----------------

The first thing you should do is reading this article `Installation <{{= url_for('%s.views.show_document' % request.appname, filename=filename) }}>`_,
you should install Uliweb correctly first according the article.

After you finished installation of Uliweb, you could already run Python and 
``uliweb`` in command line. So let go!

Creating new project
---------------------

Uliweb has already provided a command line tool named ``uliweb``, you can use
it to execute some commands. 

Go into command line and chanage to a directory which you want to create new
project of Uliweb. Then execute:

::

    uliweb makeproject hello_project
    
If the command execution is successful, it'll output nothing. It'll create a
directory named ``hello_project``. And it'll also copy some files to this 
directory. It's a very clean workspace. You can change above ``hello_project`` to
what you want.

Creating 'Hello' app
----------------------

.. code::

    cd hello_project
    uliweb makeapp Hello
    
Go into ``hello_project`` directory first, then create a new app, I named it as
``Hello``.

After the command above is executed successfully, 
you can find the following things in ``apps`` directory::

    apps/
      __init__.py
      settings.py
      Hello/
        __init__.py
        views.py
        static/
        templates/
        
Now, you can start development server to test this new project already.

Starting the server
-----------------------

::

    uliweb runserver
    
Then it may shows something in the console. You can open browser, then enter
the url http://localhost:8000. Now you can see there is a "Hello, Uliweb" message.

View module
----------------------------

When user request an url, it'll be mapped to a view function. So http://localhost:8000
also maps to a view function, you can find it in ``Hello/view.py`` file.
Open it in your favourite editor, then you will see:

.. code:: python

    #coding=utf-8
    from uliweb.core.SimpleFrame import expose
    
    @expose('/')
    def index():
        return '<h1>Hello, Uliweb</h1>'

The above code was generated automatically when you executing ``makeapp``, 
and we even don't need write any code, there is already a "Hello, Uliweb" view function!

``@expose('/')`` is used for URL Mapping, which means map the url ``'/'`` to 
the view function below. So when visiting http://localhost:8000, function ``index()`` 
will be called. If a function without being decorated by ``expose``, it will not 
be mapped to any url and is treated as a local function.

This function will return a line of HTML code that will be displayed directly in browser.

Adding templates
-------------------

If your view function returns a dict object, Uliweb will apply it to a template automatically.
It means that different return value will cause different actions.
The filename of this automatically template is the same as your view function, 
and it ends with '.html', for example, the template of ``index()`` is ``index.html``. 
Templates should be placed into the directory ``templates`` which will be automatically
created when creating a new app. Now let's add a new function to test template
process.

.. code:: python

    @expose('/template')
    def template():
        return {}

Then create a new file ``template.html`` in ``apps/Hello/templates`` with contents 
like below£º

.. code:: html

    <h1>Hello, Uliweb</h1>
    
Type http://localhost:8000/template in the browser, you will see the same thing as the previous one.

Using template variables
---------------------------

In above two examples, all data are outputed directly, this makes the app less general, 
so we're going to use template variables to change that.
Add another view function with the following code:

.. code:: python

    @expose('/template1')
    def template1():
        return {'content':'Uliweb'}

The function ``template1()`` returns a dict object with ``content`` which representing 
the content to be displayed. If you feel uncomfortable with the ``{}``, try 
this alternative:

.. code:: python

    return dict(content='Uliweb')
    
or£º

.. code:: python

    content = 'Uliweb'
    return locals()
    
The first one uses ``dict()`` to construct a dict object while 
the second one uses the builtin function ``locals()`` directly - as long as you 
define the corresponding variables in current scope. Although ``locals()`` may 
return some irrelevant variables, it is not harmful.

Then create ``template1.html`` in ``apps/Hello/templates`` with contents like below:

.. code:: html

    <h1>Hello, {{=content}}</h1>

``{{=content}}`` represents outputing value of ``content`` to template. Here you can use a 
variable or a function with return value between ``{{=`` and ``}}``.

.. note::

    The development server provided by Uliweb has the ability to reload apps, 
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
and most important, Uliweb is getting powerful!
