Architecture and Mechanism
============================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

Uliweb is also a MVT web framework.

Project Organization
-----------------------

If you download source code of Uliweb from svn, it'll contain all core components
of Uliweb, also including full `uliwebproject <http://uliwebproject.appspot.com>`_ 
site source code and other demo source code. Uliweb organize a project just like
Django, it'll split a whole project into pieces, we call them as **"Apps"**. So one
app is just a programming or organization unit, but not execution unit(like web2py).
In one project folder, there will be a ``apps`` folder, and all user apps will be
placed in it. But you can put your apps in any place you want, as soon as Uliweb
can import them directly.

In ``apps`` folder, there should be a ``setting.ini`` file. It's the global settings
file. And each app can also has its own ``setting.ini`` file. More details to see
*App Organization* section.

In Uliweb project directory, the basic directory structure is:

::

    apps/               #Store all apps
    uliweb/             #Uliweb core source code
    app.yaml            #Used for GAE deploying
    gae_handler.py      #Used for GAE deploying
    wsgi_handler.wsgi   #Used for Apache+mod_wsgi deploying
    runcgi.py           #Used for cgi/fcgi/scgi deploying
    
``apps`` folder is used for placing users apps. And Uliweb also ships with many
built-in apps, they are in ``uliweb/contrib`` folder. So you can use them directly.
        
A demonstration of structure of ``apps`` is:

::

    apps/
        __init__.py
        settings.ini                #This is global settings file
        app1/
            __init__.py
            views.py
            settings.ini
            templates/
            static/
        app2/
            __init__.py
            views.py
            settings.ini
            templates/
            static/
    
App Organization
------------------

Structure
~~~~~~~~~~~~~

One Uliweb project can be consisted by one app or several apps, and each app structure
doesn't need completely, but it should be a real Python package, so it need an
empty ``__init__.py`` file at least. So a complete app has these stuffs:

* ``settings.ini`` file, it's configure file of each app.
* ``templates`` directory used for placing template files.
* ``static`` directory used for placing static files.
* ``config.ini`` can be used to describe app dependence.

But one app may not include all of these components, it can only have:

* A ``settings.ini``, so it can just do some initalization work in it. For example:
  database configure, I18n configure, etc. It's not necessary.
* ``templates`` directory, so it can just provide public template files. It's not necessary.
* ``static`` directory, so it can just provide public static files. It's not necessary.
* Other content what you want.

Available apps
~~~~~~~~~~~~~~~~~~~~

By default, all apps in ``apps`` directory will be treated as available. So if you
start Uliweb, it'll import all apps automatically. But sometimes, you don't want
all apps are available, so you can set an ``INSTALLED_APPS`` option in ``apps/settings.ini``. 
For example:

::
    
    INSTALLED_APPS = ['Hello', 'Documents']
    
So only ``Hello`` and ``Documents`` are available apps. But if ``INSTALLED_APPS`` is empty,
Uliweb will still import all apps from ``apps`` folder. So if all apps of your project
are available you don't need to setup ``INSTALLED_APPS`` option, Uliweb will import all
available apps from ``apps`` folder automatically. So this feature will be very handy.

Apps are whole stuff logically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Even though, you can split a project into different apps physically, but you should
treat all apps as a whole stuff logically, so the stuff in ``settings.ini``, ``static`` and ``templates`` will 
be used cross apps. For example, if you create a template ``layout.html`` in A app,
and you can directly use it in B app. But if there are some same name files,
Uliweb will search current app first, then other apps. And for static files, 
Uliweb also provides command tool to extract them into one folder, so that
you can deploy them together.

In a reality project, you can have a main app, you can put public static files,
public template files in it, and even doing some database initialization process
or I18n initialization process. And other apps can also share with main app's
resource.

When using one app, it may need other apps, so you can call it dependence of apps.
And Uliweb also supports this feature simplely. You can define a ``config.ini`` in 
app folder, it content should looks like::

    [DEFAULT]
    REQUIRED_APPS = ['uliweb.contrib.i18n']
    
So when Uliweb import the app, if it find ``config.ini`` in this app folder, it'll 
parse config.ini, and insert the ``REQUIRED_APPS`` to apps list. So with this 
feature will simplify the configuration.

Startup Process
-----------------

At Uliweb startup, it'll find available apps first according above strategy. 
Then it'll **import them** all one by one. So if you have plugins hook or some
initialization process you can write them in app's ``__init__.py`` module.
Then it'll process all settings file, and 
create an ini object named ``settings`` and bind it to ``application`` object.
As you've already known, there are many settings files, one is globals 
settings.ini which in ``apps`` folder, others are apps' settings file they are in their
own folder. Uliweb will process the apps' settings files first, then the global
settings.ini. So you can write some same name options in global settings.ini to
override the apps' settings.

Then Uliweb will automatically find views module in every **availabe** app
directory. View modules are files which filename starts with ``views``. So 
``views.py`` and ``views_about.py`` are both available views module, and they'll be 
imported automatically at startup. Why doing this, because Uliweb need to 
collect all URL mapping definition from all of these view modules. 
  
URL Mapping Process
---------------------

For now, Uliweb supports two ways to manage URL definition.

One way is you can define URL by ``expose`` function in each view modules. This way is
very easy to use.

The other way is you can define URL in each view module as normal, but you can use
``extracturls`` command to dump these urls to ``apps/urls.py``, then Uliweb will automatically
find it and import it, and the ``expose`` will be automatically disabled. So if 
you like this way you can do it easily now.

There are ``expose`` and ``url_for`` functions provided by Uliweb. The former can be 
used for binding URL and view function. It's a decorator function. And the later
can be used for URL reversed creation, it'll create URL according view function
name. More details you can found at `URL Mapping <url_mapping>`_ document.

MVT Framework
---------------

Uliweb also adopts MVT framework. 

Now the Model is an ORM based on SqlAlchemy package. But there is no default ORM
binding to Uliweb, so you need choise one yourself.

View process is via functions but classes, and  when you run a view function, Uliweb
will provide an environment, and your view functions will run in it,
it very likes web2py way, but it's different approach.
web2py uses ``exec`` to run the code, however Uliweb uses ``func_globals`` inject(You can 
inject objects into function's ``func_globals`` property, so you can directly use
these injected objects without importing or declaring them.) So you can use
``request``, ``response``, etc. directly in the view function.

For template, you don't need to invoke them in commonly, just return a dict
variable from view function, and Uliweb will automatically find a matched 
template for you according the function name. For example your view function
is ``show_document()``, and the default template will be ``show_document.html``.
And if you return other type object, Uliweb will not use default template for
you. And you can assign a template filename to ``response.template`` so that
the Uliweb will not use the default matched template file but this filename.

Extending
-----------

Uliweb provides many ways to extend it:

* Plugin extension. This is a plugin mechanism. It's similar as Dispatch module,
  but I created it myself, and it's easy and simple. Uliweb has already predefined
  some plugin hook points, when it runs there, it'll find if there are some
  matched plugin hook functions existed, and will invoke them one by one.
* middleware extension. It's similar with Django. You can configure them in 
  ``settings.ini``, and it can be used for processing before or after the view
  process.
* views module initialization process. If you defined a function named as
  ``__begin__``, it'll be invoked before invoke the exact view function. So you can
  put some module level process code there. So I suggest that you can divide
  different views modules via different functionalities.

