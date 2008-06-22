manage.py 使用指南
=====================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::


manage.py是Uliweb提供的命令行工具，你可以用它做许多的事情。

runserver
-------------

启动开发服务器。

::

    Usage: python manage.py runserver [options] 
    
    options:
    
    -h hostname
    
        开发服务器的地址，缺省为localhost
        
    -p port
    
        开发服务器端口，缺省为8000
        
    --no-reloader
    
        是否当修改代码后自动重新装载代码，缺省为自动重新装载
        
    --no-debugger
    
        是否当出现错误时可以显示Debug页面，缺省为显示
        
示例：

::

    python manage.py runserver #启动缺省服务器
    
makeapp
-------------

生成一个app框架，它将自动按给定的名字生成一个app目录，同时包含有初始子目录和文件。

::

    Usage: python manage.py makeapp appname
  
示例：

::

    python manage.py makeapp Hello 
    
创建Hello应用，将在apps目录下创建一个Hello的目录，并带有初始的文件和结构。

export
--------

这个命令，可以将Uliweb的核心代码导出到你指定的outputdir目录下去。可以用于初始项目的创建。

::

    Usage: python manage.py export [options] outputdir
    
    options:
    
    -e
        完全同步操作。使用它将删除目标目录下原有的版本，然后再进行拷贝。
    
    -n
        忽略数据库组件。Uliweb自带geniusql模块，如果你不使用它，可以加这个
        选项不进行拷贝处理。
        
    -v 

        是否输出冗余信息。缺省为不输出。一旦设定将在执行时显示一些处理情况。
        
    -a appname
    
        导出某个app到指定目录下。
        
示例：

::

    python manage.py export -e ../uliweb_test   
    #完全导出到../uliweb_test目录下，以前的内容将删除
    
    python manage.py export -e -a Hello ../uliweb_test
    #完全导出Hello到../uliweb_test目录下，以前的内容将删除
    
    python manage.py export -a Hello ../uliweb_test
    #导出Hello到../uliweb_test目录下，内容将被覆盖
    
    
exportstatic
---------------

将所有已安装的app下的static文件和子目录复制到一个统一的目录下。注意，如果你在apps的
settings.py中设定了INSTALLED_APPS参数，则所有设定的app将被处理，如果没有设置，则
按缺省方式，将apps目录下的所有app都进行处理。对于存在同名的文件，此命令缺省将进行检
查，如果发现文件名相同，但内容不同的文件将会给出指示，并且放弃对此文件的拷贝。可以
在命令行使用-no-check来关闭检查。

::

    Usage: python manage.py exportstatic [options] outputdir
    
    options:
    
    -v
    
        是否输出冗余信息。缺省为不输出。一旦设定将在执行时显示一些处理情况。
        
    -no-check
    
        是否在拷贝时进行检查。缺省为检查，一旦发现不符会在命令行进行指示。如果设定为
        不检查，则直接进行覆盖。
        
示例：

::

    python manage.py exportstatic ../uliweb_test   
    #将所有已安装的app下的static文件拷贝到../uliweb_test目录下。
        
i18n
-------

i18n处理工具，用来从项目中提取_()形式的信息，并生成.pot文件。可以按app或全部app或整个
项目为单位进行处理。对于app或全部app方式，将在每个app下创建： ``app/locale/[zh]/LC_MESSAGES/uliweb.pot`` 
这样的文件。其中[zh]根据语言的不同而不同。并且它还会把.pot文件自动合并到uliweb.po文件上。

::

    Usage: python manage.py [options]
    
    options:
    
    -a appname
    
        指定要处理的appname。不能与--all, -w混用。
        
    --all
    
        处理全部的app，不能与-a, -w混用。
        
    -w
    
        整个项目处理，不能与-a, --all混用。
    
    -l locale
    
        如果没有指定则为en。否则按指定名字生成相应的目录。
        
示例：

::

    manage.py i18n -a appname -l zh #单个app的处理
    manage.py i18n --all -l zh      #全部已安装app的处理
    manage.py i18n -w               #整个apps目录的处理，缺省locale为en
    