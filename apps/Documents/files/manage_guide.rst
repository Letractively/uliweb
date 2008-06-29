manage.py User Guide
=====================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::


manage.py is a command line tool provided by Uliweb, you can use it do
many works.

runserver
-------------

Startup development server.

::

    Usage: python manage.py runserver [options] 
    
    options:
    
    -h hostname
    
        Development server host name, default is ``localhost``.
        
    -p port
    
        Development server host port, defalt is ``8000``.
        
    --no-reloader
    
        If automatically reload changed modules when you made some changes, default
        is ``True``.
        
    --no-debugger
    
        If automatically show debug page when there is exception throwed, default
        is ``True``.
        
Example:

::

    python manage.py runserver
    
makeapp
-------------

Create a new app directory structure according the given app name, it'll include
initial sub-directories and files.

::

    Usage: python manage.py makeapp appname
  
Example:

::

    python manage.py makeapp Hello 
    
It'll create a Hello app in apps directory of your project folder, the folder name
is ``Hello``.

export
--------

It'll export whole uliweb source files to target directory without apps folder.
So you can use it to create new project or update uliweb version.

::

    Usage: python manage.py export [options] outputdir
    
    options:
    
    -e
        Completely sync operation. It'll delete the old version of Uliweb in 
        outputdir directory first, then do the copy work.
        
    -v 

        Output verbose infomation, default is no output.
        
    -a appname
    
        Export a single app to target directory, you can use it to clone an app.
        
Example:

::

    python manage.py export -e ../uliweb_test   
    #Completely export Uliweb to ../uliweb_test directory, and remove old version
    
    python manage.py export -e -a Hello ../uliweb_test
    #Completely export Hello app to ../uliweb_test directory, and remove old version
    
    python manage.py export -a Hello ../uliweb_test
    #Export Hello app to ../uliweb_test directory, the old content will be overwritted.
    
    
exportstatic
---------------

Export all files from availabe apps static directory to target directory.
You can set availabe apps name in apps/settings.py via INSTALLED_APPS option, for
example: INSTALLED_APPS=['Hello', 'Documents']. If you didn't set it, all folders
in apps will be treated as an available app. When exporting static files, if there
are some files with same name, it'll be checked if the content is the same by 
default, and give you some messages in the console, and skip this file. But you
can disable this check of cause.

::

    Usage: python manage.py exportstatic [options] outputdir
    
    options:
    
    -v
    
        Output verbose information, default is not output.
        
    -no-check
    
        If check the same named files content, default is enabled, if found,
        it'll output some message and skip the file. 
        
Example:

::

    python manage.py exportstatic ../uliweb_test   
    #Export all available apps static to ../uliweb_test directory.
        
i18n
-------

I18n process tool, you can use it to extract translation catalog from
python source files and template files, the translation function is _(). 
You can process a single app or all apps by in separately or whole project.
It'll create .pot file. For app mode, the .pot file will be saved in
``yourproject/apps/appname/locale/lang/LC_MESSAGE/uliweb.pot``. For whole project mode, the 
.pot file will be saved in ``yourproject/local/lang/LC_MESSAGE/uliweb.pot``.
And lang should be different according the language which you want to deal with.
You can also use it to automatically merge .pot to existed .po file.

::

    Usage: python manage.py i18n [options]
    
    options:
    
    -a appname
    
        Process a single appname, can't be used with --all, -w together.
        
    --all
    
        Process all available apps, can't be used with -a, -w together.
        
    -w
    
        Process whole project, can't be used with -a, --all together.
    
    -l locale
    
        If not provided, it'll be ``en``. If Provided, it'll be used as language 
        name. I suggest that you should use ``en_US`` format(language_locale).
        
    -m
    
        If automatically merge .pot with existed .po file, default is not automatically 
        merge.
    
Example:

::

    manage.py i18n -a appname -l zh #Single app process
    manage.py i18n --all -l zh      #All of available apps process
    manage.py i18n -w               #Whole apps process, and using default locale ``en``.
    
extracturls
-------------

Extract URL definition from each view modules, so you should define URL via
expose() first. It'll output the urls to apps/urls.py file. And if there is
apps/urls.py, Uliweb will automatically import it then disable expose(). 

::

    Usage: python manage.py extracturls
    
If there is already a urls.py file in apps directory, it'll prompte you
to confirm you want to overwrite it.
