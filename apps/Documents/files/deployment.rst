部署指南
=============

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

Apache
---------

mod_wsgi
~~~~~~~~~~~

#. 按 `mod_wsgi <http://code.google.com/p/modwsgi/>`_ 的说明安装mod_wsgi到apache下。

   * 拷贝mod_wsgi.so到apache的modules目录下

   Window环境可以看：

    http://code.google.com/p/modwsgi/wiki/InstallationOnWindows

   Linux环境可以看：

    http://code.google.com/p/modwsgi/wiki/InstallationOnLinux


#. 配置 apache 的httpd.conf文件

   * 增加：

     ::
    
        LoadModule wsgi_module modules/mod_wsgi.so
        WSGIScriptAlias / /path/to/uliweb/wsgi_handler.wsgi
        
        <Directory /path/to/youruliwebproject>
        Order deny,allow
        Allow from all
        </Directory>
        
     如果在windows下，示例为：
    
     ::
    
        WSGIScriptAlias / d:/project/svn/uliweb/wsgi_handler.wsgi
        
        <Directory d:/project/svn/uliweb>
        Order deny,allow
        Allow from all
        </Directory>

#. 重启apache        