Architecture and Mechanism
============================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

Uliweb is also a MVT web framework, and it's released under GPLv2 license.

Project Organization
-----------------------

If you download Uliweb's source code from svn, it'll contain all core components
of Uliweb, also including full `uliwebproject <http://uliwebproject.appspot.com>`_ 
site source code and other demo source code. Uliweb adopts the similar management
from web2py, i.e. core source code are put with application source code, this
way will reduce the trouble at deploy. But the organization of project is more 
like Django, but not like web2py. All apps will be organized together into a whole
site. They are placed in ``apps`` folder of your project directory, by default,
all apps will available, but you can also define which apps are truely available
in apps/settings.py. And the app organization in Uliweb is more complete, each
app can has it own:

* settings.py file, it's configure file of each app.
* templates directory used for placing template files.
* static directory used for placing static files.

This organization way make app level reuse of Uliweb is more flexiable and easier.

In Uliweb project directory, the basic directory structure is:

::

    apps/               #Store all apps
        sqlalchemy/     #Default database driven module
        migrate/        #migrate package of sqlalchemy
        webob/          #Create Request, Response object
        werkzeug/       #Underlying module
    uliweb/             #Uliweb core source code
    app.yaml            #Used for GAE deploying
    gae_handler.py      #Used for GAE deploying
    manage.py           #Command line management tool
    wsgi_handler.wsgi   #Used for Apache+mod_wsgi deploying
    
And structure of Uliweb is:

::

    uliweb/
        core/           #Core component
        i18n/           #Internationalization process module
        middlewares/    #Middleware collection directory
        orm/            #Uliorm module
        test/           #Testing scripts
        utils/          #Utils modules
        
structure of apps is:

::

    apps/
        __init__.py
        settings.py
        app1/
            __init__.py
            settings.py
            templates/
            static/
        app2/
            __init__.py
            settings.py
            templates/
            static/
    
App Organization
------------------

One Uliweb project can be consisted by one app or several apps, and each app structure
doesn't need completely, but it should be a real Python package, so it need an
empty __init__.py file at least. So one app can be:

* Has only a settings.py, so it can just do some initalization work in it, for example:
  database configure, I18n configure, etc.
* Has only templates directory, so it can just provide public template files.
* Has only static directory, so it can just provide public static files.
* Other content what you want.

By default, all apps in ``apps`` directory will be treated as available. So if you
startup Uliweb, it'll process all apps automatically. But sometimes, you don't want
all apps are available, so you can set an INSTALLED_APPS option in apps/settings.py, 
for example:

::
    
    INSTALLED_APPS = ['Hello', 'Documents']
    
So only ``Hello`` and ``Documents`` are available apps.

At Uliweb startup, it'll automatically import settings.py from **available** apps.
And it'll combine all configure options into a dict variable named ``config`` at the
end. And you should notice that option variable name should be written in upper 
case. Because settings.py will automatically imported at startup time, so you can
also write some initialization code in there, for example: database initialization,
etc.

And at Uliweb startup, it'll automatically find views module in every **availabe** app
directory. And views module are files which filename starts with ``views``. So 
``views.py`` and ``views_about.py`` are both available views module, and they'll be 
imported automatically at startup. Why doing this, because Uliweb need to 
collect all URL mapping definition from all of these views modules. 
  
So in a reality project, you can have a main app, you can put public static files,
public template files in it, and even doing some database initialization process
or I18n initialization process. And other apps can also share with main app's
resource.

When you want to access a template file or static file, Uliweb will search in
current app directory, if it can't find the file, it'll search from others directory.
So you can treat all apps as an entirety.

URL Mapping Process
---------------------

For now, Uliweb supports two ways to manage URL definition.

One way is you can define URL by expose function in each view modules. This way is
very easy to use.

The other way is you can define URL in each view module as normal, but you can use
extracturls command to dump these urls to apps/urls.py, then Uliweb will automaticall
find it and import it, and the expose will be automatically disabled. So if 
you like this way you can do it easilynow.

There are ``expose`` and ``url_for`` functions provided by Uliweb. The former can be 
used for binding URL and view function. It's a decorator funtion. And the later
can be used for URL reversed creation, it'll create URL according view function
name. More details you can found at `URL Mapping <url_mapping>`_ document.

MVT Framework
---------------

Uliweb also adopts MVT framework. 

Now the Model is an ORM based on SqlAlchemy package.

View is using function but not class, but when you run a view function, Uliweb
will provide an environment for it, it very likes web2py way, but it's different.
web2py uses ``exec`` to run the code, however Uliweb uses f_globals inject(You can 
inject variables into function's ``func_globals`` property, so you can directly use
these injected objects without importing or declaring them.) So you can use
``request``, ``response``, etc. directly in the view function.

For template, you don't need to invoke them in commonly, just return a dict
variable from view function, and Uliweb will automatically find a matched 
template for you according the function name. For example your view function
is ``show_document()``, and the default template will be ``show_document.html``.
And if you return other type object, Uliweb will not use default template for
you. And you can assign ``response.template`` a template name to replace the
default template.

Extending
-----------

Uliweb provides many ways to extend it:

* Plugin extension. This is a plugin mechanism. It's similar as Dispatch module,
  but I created it myself, and it's easy and simple. Uliweb has already predefined
  some plugin invoke points, when it runs there, it'll find if there are some
  matched plugin existed, and will invoke them one by one.
* middleware extension. It's similar with Django. You can configure them in 
  apps/settings.py, and it can be used for processing before or after the view
  process.
* views module initialization process. If you defined a function named as
  ``__begin__``, it'll be invoked before invoke the exact view function. So you can
  put some module level process code there. So I suggest that you can divide
  different views modules via different functionalities.

