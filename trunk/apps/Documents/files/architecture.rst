Architecture, structure and programmatical execution 
=====================================================

:Authors: Limodou <limodou@gmail.com>, Sharriff <sharriff.aina@merkuri.de>

.. contents:: 
.. sectnum::

Uliweb is a Python web application framework that utilizes a MVT architecture.

MVT Framework
---------------

The **M** or Model is an ORM based on SqlAlchemy package. You are however not
restricted to using Uliwebs ORM. You can choose another ORM package of your choice.

The **V** or View process is accomplished via functions or callable classes. When 
view function is run, Uliweb will provide an environment for the the view to run in
Uliweb uses ``func_globals`` inject(You can inject objects into function's ``func_globals`` property, so you can directly use
these injected objects without importing or declaring them.) So you can use
``request``, ``response``, etc. directly in the view function.

For template, you don't need to invoke them in commonly, just return a dict
variable from view function, and Uliweb will automatically find a matched 
template for you according the function name. For example your view function
is ``show_document()``, and the default template will be ``show_document.html``.
And if you return other type object, Uliweb will not use default template for
you. And you can assign a template filename to ``response.template`` so that
the Uliweb will not use the default matched template file but this filename.


Project Organization
-----------------------

If you followed the instructions of getting and installing Uliweb from its SVN
repository, you will notice it contains not only the core of the Uliweb framework,
but also example source code and the code of the Uliweb `uliwebproject <http://uliwebproject.appspot.com>`_ 
site itself.

A web application is defined as a **Project** in Uliweb. An Uliweb web application Project
consists of any number of smaller components. These components can be complete applications
called **Apps** in Uliweb speak, middleware, plugins, Uliweb core applications or Python modules of your own.

The basic directory structure of an Uliweb Project is as follows:

::

    apps/               #Uliweb applications are placed here
    uliweb/             #Uliweb core source code
    app.yaml            #Used for deploying GAE based applications
    gae_handler.py      #Used for deploying GAE based applications
    wsgi_handler.wsgi   #Used for deploying applications using Apache+mod_wsgi 
    runcgi.py           #Used for deploying applications using cgi/fcgi/scgi    

    
App Organization
------------------

Structure
~~~~~~~~~~~~~

Uliweb applications are placed in the ``apps`` folder. Uliweb also ships with many
built-in apps, they are stored in the ``uliweb/contrib`` folder.

There is a global settings file for all apps in the ``apps`` folder called ``setting.ini`` . 
Each app can have its own ``setting.ini`` file for initialisation and configuration purposes. For more details to see
*App Organization* section.

An Uliweb **app** in its basic form is actually Python package, this implies the precense
of an empty ``__init__.py`` file in its root folder. Further, an **app** may have the following
components:

* ``settings.ini`` file, the configuration file of te app.
* ``templates`` directory, used to store template files.
* ``static`` directory used to store static files.
* ``config.ini`` can be used to define app dependencies.

A ``settings.ini`` can be used to carry out some initalization work. For example, 
database, I18n configuration etc. 
        
A example of what an ``apps`` folder structure in an project could look like is below:

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


Application availability
~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, all apps in ``apps`` directory are made available to the project, all appare imported
automatically. You can change this feature by defining an ``INSTALLED_APPS`` option
in the ``apps/settings.ini`` file. 

For example:

::
    
    INSTALLED_APPS = ['Hello', 'Documents']
    
This restricts the apps made available to the project to ``Hello`` and ``Documents`` only
. If ``INSTALLED_APPS`` is empty, or you omit it entirely, it defaults to importing 
and making all the apps available automatically. A very hand feature.

Apps are logically complete components
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Even though you can split a project( complete web application) into different apps physically, every app should be treated
as a logically complete component. This is however, not a rule or restriction as 
Uliweb is flexible enough to allow the components in an **app**, for exmple the ``settings.ini`` file, 
the ``static`` and ``templates`` to be made available to other **apps** to facilitate cross-application
communication. For example, if you create a template ``layout.html`` in an app **A**,
you can directly use it in an app called **B**. 

In a deployed production project, you could, for example, have a main app that contains all the globally available static and template files. It could even take care of I18n and database initialisation processes.

Creating dependencies between apps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you intend to make an app dependant on abother app or more, you can define the dependancies
in a ``config.ini`` file and then place this file in the app that 
app folder, it content should looks like::

    [DEFAULT]
    REQUIRED_APPS = ['uliweb.contrib.i18n']
    
So when Uliweb import the app, if it find ``config.ini`` in this app folder, it'll 
parse config.ini, and insert the ``REQUIRED_APPS`` to apps list. So with this 
feature will simplify the configuration.

Startup and initialisation process
-----------------

When an Uliweb project starts up, it searches the apps folder and imports all of them one by one. This means that
during an app import, plugin hooks or other initialization procedures are processed. 
Code in an app's ``__init__.py`` module is prcessed first, after that, it will process the apps
settings file, and create an ini object named ``settings`` and bind it to ``application`` object.

Options placed in global settings.ini file can override the settings in an individual apps
settings file.

The next step will be that Uliweb will automatically find views module in every **available** apps
directory. This is necessary as Uliweb neds to collect all the defined URL mappings in these modules.
View files are files which start with ``view``. So 
``view.py`` and ``view_about.py`` are both available views module, and they'll be 
imported automatically at startup. 
  
URL Mapping Process
---------------------

At present, Uliweb supports two ways to definé URLs in views.

One way is to define a URL by using the ``expose`` decorator. This is the easier method.
The other way is to define the URLs in each view module as normal, and then use the 
``extracturls`` command to dump these urls to the ``apps/urls.py`` file. Uliweb will automatically
find and import it, the ``expose`` would therby be be automatically disabled.

To assist in URL management, Uliweb provides an ``url_for`` function. This function
can be used for reversed URL creation, it'll create URLs according to the correspondingview function
name. For more details, see the `URL Mapping <url_mapping>`_ document.b

Extending Uliweb
-------------------

Uliweb provides many ways to extend its functionality:

* Plugin extensions. This plugin mechanism is similar to the Dispatch module, but much easier.
  Uliweb has already predefined plugin hook points, if there is a plugin that implements one of the hooks dfined by the Uliweb
  Plugin mechanism, it would be invoked at that point.
* middleware extension. It's similar to Djangos. You can configure them in 
  ``settings.ini``, and it can be used for processing before or after the view
  process.
* views module initialization process. If you define a function that starts with the prefix
  ``__begin__``, it'll be invoked before view function. This allows you to include
  put some module level code there. The preffered method would be to divide the different
  views modules according to their different functionalities.

