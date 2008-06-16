版本升级
=============

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

通常情况下你不会直接在Uliweb的源码目录下进行工作，因为它包含了uliwebproject的源码。所以
你会将源码导出到一个可工作的目录下。那么Uliweb提供了：

::

    python manage.py export [-e] [-n] outputdir
    
    -e
        完全同步操作。使用它将删除目标目录下原有的版本，然后再进行拷贝。
    
    -n
        忽略数据库组件。Uliweb自带geniusql模块，如果你不使用它，可以加这个选项不进行拷贝处理。
    
这个命令，可以将Uliweb的核心代码导出到你指定的outputdir目录下去。

一旦当Uliweb的源码更新了，你仍然可以继承使用上面的命令将新的源码导出到ouputdir目录下。

.. note::

    如果原来的文件删除了，这种导出不会自动删除无用的文件。因此如果你想完全进行替换，并且
    删除不同步的文件，那么可以增加 -e 参数在export之后。