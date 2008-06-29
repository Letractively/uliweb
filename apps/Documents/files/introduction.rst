=====================
Uliweb Introduction
=====================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

What's it?
------------

Uliweb is a new brand Python Web Framework. Before creating this framework,
I've learned and used many frameworks, Karrigell, Cherrypy, Django, web2py,
but more or less they are not fully satisfy me. So I decide to create myself
web framework, I hope I can merge their advantages into Uliweb, and I'll
try to make it simple and easy to use.

This project is created and leaded by Limodou <limodou@gmail.com>. And it has
received many helps from many kind people.

License
------------

Uliweb is released under GPL v2 license.

Infrastructure
----------------

It's not a totally created from scratch, I've used some modules, for example:

* `Werkzeug <http://werkzeug.pocoo.org/>`_ Used in core process of framework, 
  for example: command line, URL Mapping, Debug, etc.
* `webob <http://pythonpaste.org/webob/>`_  Used to create Request, Response
  object, and static file process.
* `SqlAlchemy <http://www.sqlalchemy.org>`_ I wrapped an ORM based on it,
  so you can use ORM to access database, and you can also use this module directly.

I also reference some code from other frames, for example:

* template Borrow from `web2py <http://mdp.cti.depaul.edu/>`_ and I made some 
  improvement.
* Some code referenced from `Django <http://www.djangoproject.com/>`_ project.

And I also made some new "wheels" myself, for example:

* Form process, you can use it to create HTML code, validate submitted data and 
  convert submitted data to Python data type.
* I18n process, including template support, language lazy process.
* Uliorm, it an ORM module, built on SqlAlchemy now, and I also referenced from 
  GAE datastore modeul.
* Framework runtime process.
* Plugin mechanism, I borrowed from `UliPad <http://code.google.com/p/ulipad>`_ project.

Features
-----------

* Organization

  * MVT(Model View Template) development model.
  * Distributed development but unified management. Uliweb organizes project with
    small apps. Each app can has it own configure file(settings.py), templates 
    directory, static directory. So you can easily reuse app. But when you run 
    the project, you can treat all apps as a whole app, and you can also reference
    each other static files and templates. If you don't config INSTALLED_APPS in
    configure file, all apps will available by default. And all configure files
    of all available apps will be automatically processed at project startup,
    and finally you can get a complete configure view.

* URL Mapping

  * Flexiable and powerful URL mapping. It uses werkzeug's routing module, 
    you can define URL easily, and you can bind URL with view function easily too.
    You can also create URL reversed according view function name. It supports
    arguments definition in URL. And it also support default URL mapping to a 
    view function.
    
* View and Template

  * View template can be automatically applied. If you return a dict variable from
    view function, Uliweb will automatically find a default applied template according
    the view function name.
  * Environment execution mode. Each view function will be run in an environment,
    so you don't need to write many import statements, and there are already many
    objects can be used directly, for example: request, response, etc. It can reduce
    many code.
  * You can directly use Python code in template, and you don't need to consider
    indent in code, just remember add pass statement at the end of a block. It also
    supports include child template and inherit from parent template.
    
* ORM

  * Uliorm is default ORM module but not default configured, you can use any 
    ORM module you like.
  * Uliorm supports models and database automatically migirate, including
    table creation and table structure modification.

* I18n

  * Supports python file and template file.
  * Supports browser language setting and cookie setting, automatically language switch.
  * Provide command line tool, you can use it to extract .po files. It can support
    app level or project level process. It can automatically merge .pot to existed
    .po file.
    
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

  * Uliweb is a project with demos. It includes all core code and also all 
    source code of `uliwebproject <http://uliwebproject.appspot.com>`_ , and some
    other demos code, so you can directly use these code.
  * Uliweb supports static file access directly, and it can also process
    HTTP_IF_MODIFIED_SINCE and return static file content in trunk.
    
Goals
----------

* Developing a simple and easy use framework.
* Flexiable enought and easy to extend.
* Including enough example code.
* Writing clear and easy understand documents.
* Can be deployed in many platforms.