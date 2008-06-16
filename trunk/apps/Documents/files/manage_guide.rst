manage.py 使用指南
=====================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::


manage.py是Uliweb提供的命令行工具，你可以用它做许多的事情。

export
--------

这个命令，可以将Uliweb的核心代码导出到你指定的outputdir目录下去。可以用于初始项目的创建。

::

    Usage: python manage.py [options] outputdir
    
    options:
    
    -e
        完全同步操作。使用它将删除目标目录下原有的版本，然后再进行拷贝。
    
    -n
        忽略数据库组件。Uliweb自带geniusql模块，如果你不使用它，可以加这个
        选项不进行拷贝处理。


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
    
makeapp
-------------

生成一个app框架，它将自动按给定的名字生成一个app目录，同时包含有初始子目录和文件。

::

    Usage: python manage.py makeapp appname
    
exportapp
-------------

复制指定的app代码到目标目录下的apps子目录中。你可以用它来方便的Clone一个app。

::

    Usage: python manage.py exportapp outputdir
    
exportstatic
---------------

将所以生效的app下的static文件和子目录复制到一个统一的目录下。注意，如果你在apps的
settings.py中设定了INSTALLED_APPS参数，则所有设定的app将被处理，如果没有设置，则
按缺省方式，将apps目录下的所有app都进行处理。对于存在同名的文件，此命令缺省将进行检
查，如果发现文件名相同，但内容不同的文件将会给出指示，并且放弃对此文件的拷贝。可以
在命令行使用-no-check来关闭检查。

::

    Usage: python manage.py [options] exportstatic outputdir
    
    options:
    
    -v
    
        是否输出冗余信息。缺省为不输出。一旦设定将在执行时显示一些处理情况。
        
    -no-check
    
        是否在拷贝时进行检查。缺省为检查，一旦发现不符会在命令行进行指示。如果设定为
        不检查，则直接进行覆盖。