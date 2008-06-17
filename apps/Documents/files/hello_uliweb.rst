Hello, Uliweb
================

:Author: Limodou <limodou@gmail.com>

.. contents:: 

本教程将带你领略 Uliweb 的风采，这是一个非常简单的例子，你可以按照我的步骤来操作。我们
将生成一个空的页面，它将显示"Hello, Uliweb"信息。

准备
-----

从 http://code.google.com/p/uliweb 下载最新版本或从svn中下载最新版本，放在一个目录下。
因为 Uliweb 本身包含 uliwebproject 网站的代码，所以在我们这个简单的例子中其实是不需要的。
它们都存在于apps目录下。一种方式是你将它全部删除，因为我们会创建新的app。另一种方式就是修
改apps下的settings.py文件，只让我们新创建的app生效。再一种方法就是将代码导出到其它的工作
目录下，这样环境比较干净，然后开始工作。这里我们将采用第三种方法。

创建新的项目
-------------

Uliweb 提供一个命令行工具 manage.py, 它可以执行一些命令。在Uliweb的下载目录下，进入命
令行，然后执行：

::

    python manage.py export ../uliweb_work
    
这里export后面是一个目录，我是将它建在与uliweb同级的uliweb_work下了，你可以换成其它的目录。

在执行成功后(成功不会显示任何内容)，在命令行进入新建的目录，在这个目录下是一个完整的Uliweb
的拷贝，但是没有任何APP存在，所以是一个干净的环境。

创建Hello应用
--------------

然后让我们创建一个Hello的应用。在uliweb_work目录的命令行下执行：

.. code::

    python manage.py makeapp Hello
    
在执行成功后，你会在apps下找到::

    apps/
      __init__.py
      settings.py
      Hello/
        __init__.py
        settings.py
        views.py
        static/
        templates/
        
好了，现在 Hello 已经创建好了。再一步就是如何创建“Hello, Uliweb”了。

输出"Hello, Uliweb"
---------------------

打开 Hello/views.py，你会看到

.. code:: python

    #coding=utf-8
    from uliweb.core.SimpleFrame import expose

    @expose('/')
    def index():
        return '<h1>Hello, Uliweb</h1>'
    
以上几行代码是在执行 makeapp 之后自动创建的。甚至我们都不用写一行代码，已经有一个
Hello, Uliweb 的View函数了。

@expose('/') 是用来处理 URL Mapping的，它表示将/映射到它下面的view方法上。这样，当用户
输入 http://localhost:8000/ 时将访问 index() 方法。如果一个函数前没有使用expose修饰，
它将不会与任何URL对应，因此可以认为是一个局部函数。

这里index()没有任何参数。如果你在expose中定义了参数，它将与之对应。但因为这个例子没有定
义参数，因此index不需要定义参数。

然后我们直接返回了一行HTML代码，它将直接输出到浏览器中。

启动
------

好了，让我们启动看一下结果吧。

在命令行下执行

.. code:: console

    python manage.py runserver
    
这样就启动了一个开发服务器。然后可以打开浏览器输入: http://localhost:8000 看到结果。

是不是很简单，但是这样不够，让我们变化一下，这次让我们加入模板。

加入模板
---------

如果你的 view 方法返回一个dict对象，则 Uliweb 会自动为你应用一个模板，模板名字与你的view
方法一样，只不过后面有一个 .html。如 index() 对应的模板就是 index.html。那么这个模板文件
放在哪里呢？在前面你可以看到，当你创建完一个 app 之后，会自动创建一个 templates 目录，因
此你的模板就放在这个 templates 目录下。好，为了不影响index()方法，让我们创建一个新的方法

.. code:: python

    @expose('/template')
    def template():
        return {}

然后在apps/Hello/templates下创建 template.html, 内容为：

.. code:: html

    <h1>Hello, Uliweb</h1>
    
在浏览器输入 http://localhost:8000/template 你将看到相同的结果。

使用模板变量
-------------

上面的例子是将信息全部放在了模板中，但是这样通用性不好，现在再让我们修改一下，使用模板变量。
让我们再创建一个新的view方法，写入下面的代码

.. code:: python

    @expose('/template1')
    def template1():
        return {'content':'Uliweb'}

然后在apps/Hello/templates下创建 template1.html，内容为：

.. code:: html

    <h1>Hello, {{=content}}</h1>
    
这次我在template1()中返回了一个字典，则变量content将用来表示内容。也许你对使用 {} 这样
的形式感觉不够方便，还有以下的变形的方式，如：

.. code:: python

    return dict(content='Uliweb')
    
或：

.. code:: python

    content = 'Uliweb'
    return locals()
    
前一种方法利用dict函数来构造一个dict对象。而后一种方法则直接使用了locals()内置函数来返
回一个dict对象，这样你只要定义了相应的变量就可以了。这样locals()返回的变量有可能比模板
所需要的变量要多，但是不会影响你的使用，只要在模板中认为不存在就可以了。

.. note::

    使用 Uliweb 的开发服务器具备自动重启的功能，因此一般进行程序的修改不需要重启服务器，
    只要刷新浏览器就行。但有时程序出错或一些模板具备缓冲能力还是需要刷新。只要在命令行下
    输入 Ctrl+C 就可以结束开发服务器，然后重启就行。

结束
------

本教程只演示了最基本的 view 和模板的处理，还有其它许多的内容没有涉及，如：

* App的组织
* 数据库的使用
* 配置文件的使用
* 等等

许多内容可以从 http://uliwebproject.appspot.com 上找到，而且 Uliweb 本身也在不停发展
之中。