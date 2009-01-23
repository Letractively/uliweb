=====================
Uliweb Introduction
=====================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

What is Uliweb?
----------------

Uliweb is a new Python Web Framework. Before I started to create this framework,
I had used a few other frameworks such as Karrigell, Cherrypy, 
Django and web2py, but they did satisfy me due to several reasons. I then decided 
to create a web framework that combined the strengths of these frameworks, keeping in mind
that the main focus is to make Uliweb easy to use yet powerful.

This project was created and lead by Limodou <limodou@gmail.com>. It is in constant development 
from several other developers around the world.

License
------------

Uliweb is released under GPL v2 license.

Infrastructure
----------------

Uliweb was not created totally from scratch. It uses some modules created by 
other developers, for example:

* `Werkzeug <http://werkzeug.pocoo.org/>`_ Used in core process of framework. 
  For example: command line, URL Mapping, Debug, etc.
* `webob <http://pythonpaste.org/webob/>`_  Used to create Request, Response
  object, and static file process.
* `SqlAlchemy <http://www.sqlalchemy.org>`_ I wrapped an ORM based on it.
  So Uliweb user can use ORM to access a database, or use this module directly.

I also referenced some code from other web frameworks, for example:

* Template was borrowed from `web2py <http://mdp.cti.depaul.edu/>`_ and I made some 
  improvements.
* Some codes were referenced from `Django <http://www.djangoproject.com/>`_ project.

And I also constructed a few new "wheels" myself. For example:

* Form process, developers can use it to create HTML code, validate submitted data and 
  convert submitted data to Python data types.
* I18n processing including template support, language lazy process.
* Uliorm, which is an ORM module, was built on top of SqlAlchemy. I also referenced from 
  GAE datastore module.
* Framework runtime process.
* Plugin mechanism, borrowed from `UliPad <http://code.google.com/p/ulipad>`_ project.

Features
-----------

* Organization

  * MVT(Model View Template) development model.
  * Distributed development but unified management. Uliweb organizes a project with
    small apps. Each app can has its own configuration file(settings.ini), templates 
    directory, and static directory. Previouly created app can be easily reused. But 
    when user runs the project, all apps can be treated as a whole app. User can also 
    reference other static files and templates. If INSTALLED_APPS is not configured in
    the configuration file, all apps will be available by default. And all configuration
    files for all available apps will be automatically processed at project startup, 
    which gives the user a complete configuration view.

* URL Mapping

  * Flexiable and powerful URL mapping. Uliweb uses werkzeug's routing module. 
    User can easily define a URL, which in turn can be easily binded with a view function.
    URL can also be created reversely according to the view function name. It supports
    arguments definition in URL. And it also supports default URL mapping to a 
    view function.
    
* View and Template

  * View template can be automatically applied. If you return a dict variable from
    view function, Uliweb will automatically find a default applied template according
    to the view function name.
  * Environment execution mode. Each view function will be run in an environment,
     which eliminates the need to write many import statements. Plus there are already many
    objects that can be used directly, for example: request, response, etc. When used, 
    these objectsIt can save many lines of code.
  * User can directly use Python code in a template, and user does not need to indent
    his code, as long as he remembers to add a pass statement at the end of each block. 
    Uliweb also supports including of child template and inheriting from parent template.
    
* ORM

  * Uliorm is the default ORM module but not configured by default, user can use any 
    ORM module as he prefers.
  * Uliorm supports models and automatic database migiration, including table creation 
    and table structure modification.

* I18n

  * Supports python file and template file.
  * Supports browser language setting and cookie setting, and automatic language switch.
  * Provides command line tool. User can use it to extract .po files. It can support
    app level or project level process. It can automatically merge .pot files to existing
    .po files.
    
* Extension

  * Plugin extension. This is a plugin process mechanism. There are already some
    plugin invoke points in Uliweb. So you can write some procedures and bind them
    to these points, in order to finish some special works. For example, database
    initicalization, I18n process initialization, etc.
  * middleware extension. It's similar with Django. You can configure it in configure
    files. Each middleware can process request and response.
  * views module initial process. If you write a special function named __begin__,
    it'll be processed before any view function can be processed, so you can do
    some module level process here, for example: check the user authentication, etc.
    So I suggest that you devide different view modules according different 
    functionality.
    
* Command Line Tools

  * Export a clear environment to a special directory. Then you can work from there.
  * Create app, and include the essential directory structure, files and code.
  * Export static files, you can export all available apps' static files to a
    special directory.
  * Startup a developing web server, support debug and automatically reload.

* Deployment

  * Support GAE, it's very easy.
  * Support mod_wsgi, cgi, fast_cgi, scgi.

* Development

  * Provide a development server, and can be automatically reload when some
    module files are modified.
  * Enable debug, you can check the error traceback, and it also supports
    template debugging.

* Others

  * Various demos are available for anyone interested in learning more about Uliweb. 
    It includes all core codes and also all source code of `uliwebproject <http://uliwebproject.appspot.com>`_ , 
    and some other demo codes, which can be used directly/freely as you wish.
  * Uliweb supports static file access directly, and it can also process
    HTTP_IF_MODIFIED_SINCE and return static file content in trunk.
    
Goals
----------

* Developing a simple and easy to use web framework.
* The web framework should be flexiable and easy to extend.
* The web framework should be able to be deployed in different platforms.
* Providing enough sample codes for using this framework.
* Providing concise and easy to understand documentation for this framework.

