=====================
Uliweb Introduction
=====================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

About Uliweb
----------------

Uliweb is a Python based web framework. 

This project was created by Limodou <limodou@gmail.com>.

License
------------

Uliweb is released under BSD license.

Infrastructure
----------------

Uliweb was not created totally from scratch. It uses some modules created by 
other developers, for example:

* `Werkzeug <http://werkzeug.pocoo.org/>`_ Used to handle core processes in the framework. 
  For example: command line tools , URL Mapping, Debug, etc.
* `SqlAlchemy <http://www.sqlalchemy.org>`_ The ORM based on it. Developers can access
  databases, or use the module separately.

I also referenced some code from other web frameworks, for example:

* The Templating system is styled after the one used in `web2py <http://mdp.cti.depaul.edu/>`_ several 
  improvements were made.

I also constructed a few new "wheels" myself. For example:

* Form processing module. Developers can use it to create HTML code, validate submitted data and 
  convert submitted data to Python data types.
* I18n processing including template support, language lazy process.
* Uliorm, which is an ORM module, was built on top of SqlAlchemy. 
* Framework runtime process.
* Plugin mechanism, styled after the one used in the `UliPad <http://code.google.com/p/ulipad>`_ project.
* weto is a cache and session package. 
* pyini used to parse settings.ini.

Features
-----------

* Organization

  * MVT(Model View Template) development model.
  * Distributed development but unified management. Uliweb organizes a project with
    small apps. Each app can have its own configuration file(settings.ini), template 
    directory, and static directory. Existing apps can be easily reused, but are treated as a compound. 
    web application project if configured as such. Developers can also 
    reference static files and templates between apps, thus easing inter-application data exchange. 
    All apps in a project are loaded by default if INSTALLED_APPS is not configured in
    the configuration file. All separate app configuration files are automatically processed at 
    project startup.

* URL Mapping

  * Flexiable and powerful URL mapping. Uliweb uses werkzeug's routing module. 
    User can easily define a URL, which in turn can be easily bound with a view function.
    URLs can also be created reversely according to the view function name. It supports
    argument definitions in URLs and default URL mapping to a 
    view function.
    
* View and Template

  * View templates can be automatically applied. If you return a dict variable from
    view function, Uliweb will automatically try to match and apply a template according
    to the view function name.
  * Supports function-based view and class-based view.
  * Provides generic functionalities and make model-based view process is easily.
  * Environment execution mode. Each view function will be run in an environment,
    which eliminates the need to write many import statements. Plus there are already many
    objects that can be used directly, for example: request, response, etc. This is DRY and saves a lot of coding
  * Developers can directly use Python code in a template, the Python code does not neede to be indented
    as long as a pass statement is added at the end of each code block. 
    Uliweb also supports child template inclusion and inheritance.
    
* ORM

  * Uliorm is the default ORM module but not configured by default. Developers are free to use any 
    ORM module as preferred.
  * Uliorm provides command line to do creating, dropping, dumping, loading things.
  * Uliorm supports OneToOne, ManyToOne, ManyToMany relationships.

* I18n

  * Can be used in python and template files.
  * Browser language and cookie settings are supported including automatic language switching.
  * Provides a command line tool that developers can use to extract .po files. 
    This can happen either at the app level or project level process. It can automatically merge .pot files to existing
    .po files.
    
* Extension

  * Dispatch extension. This is a dispatch processing mechanism that utilizes different 
    types of dispatch points. So you can write procedures to carry out 
    special processes and bind them to these dispatch points. For example, database
    initicalization, I18n process initialization, etc.
  * middleware extension. It's similar to Djangos. You can configure it in configuration
    files. Each middleware can process the request and response objets.
  * Special function calls in the views module initial process. If you write a special 
    function named __begin__, it'll be processed before any view function can be processed, 
    this allows developers to do some module level processing at that point, for example: 
    check the user authentication, etc.
    
* Command Line Tools

  * Create app, and include the basic essential directory structure, files and code.
  * Export static files, you can export all available apps' static files to a
    special directory.
  * Startup a development web server thats supports debugging and autoreload.
  * Several project and app management tools.

* Deployment

  * Supports easy deployment on the GAE platform.
  * SUpports dotcloud deployment.
  * Supports mod_wsgi, cgi, fast_cgi, scgi.

* Development

  * Provide a development server, and can be automatically reload when some
    module files are modified.
  * Enhanced debugging, you can check the error traceback, template debugging is also supported.

Principle
----------

* Simple and easy to use web framework.
* Reusability and configurable are the main ideas about Uliweb.
* The web framework should be flexiable and easy to extend.

Links
--------

* Plugs is a Uliweb apps collection project, you can visit it at https://github.com/limodou/plugs
* uliweb-doc is a documentation project of Uliweb, you can visit it at https://github.com/limodou/uliweb-doc, 
  and you can also read the compiled documentation at http://uliweb.rtfd.org
* uliwebzone is a community project of Uliweb, you can visit it at https://github.com/limodou/uliwebzone, 
  and you can also see online demo which hosted in dotcloud http://www.uliweb.dotcloud.com/.