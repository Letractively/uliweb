安装说明
==========

目前 Uliweb 还没有发布正式版本，因此你要首先从svn下载代码，

.. code::

    svn checkout http://uliweb.googlecode.com/svn/trunk/ uliweb
    cd uliweb
    python setup.py develop

使用develop安装只会在Python/site-packages下建一个链接，并不会真正安装，好处就是更新方便。

当然你也可以直接通过 install 来安装。

.. code::

    python setup.py install