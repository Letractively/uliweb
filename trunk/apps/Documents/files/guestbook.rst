Mini GuestBook
================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

Maybe you've learned `Hello, Uliweb <hello_uliweb>`_ this tutorial, and have some
sense to Uliweb, so, let's step into database world together, and see how to 
use database simply.

Prepare
---------

There is already the whole GuestBook source code in Uliweb apps directory.
Just download the newest source code of Uliweb, then start developing server:

::

    python manage.py runserver
    
Enter http://localhost:8000/guestbook in the browser, then you'll find it.
By default, it'll use sqlite3, so if you are using Python 2.5, you'll not need
to install sqlite Python binding module. Or you need to install pysqlite2 package
yourself. For now, Uliweb uses geniusql for underlying database driven module,
it already supports many database, such as: mysql, sqlite, postgresql, sqlserver, 
access, firebird. But I just test with sqlite3 and mysql. Before you want to use
other databases, you should also install their database module first.

Ok, let's begin to write code.

Create Project
----------------

I suggest that you begin your work at a new directory, and Uliweb provides an 
``export`` command, for example:

::

    python manage.py export outputdir
    
So it'll export all necessary Uliweb source code to outputdir directory. Then
goto this directory, ready to begin.

Create App
-----------

Goto the project directory built in previous step, and use ``makeapp`` to create a
new app.

::

    python manage.py makeapp GuestBook
    
This will automatially create a ``GuestBook`` app for you in ``apps`` 
directory of your project.

Configure Database
--------------------

Uliweb indeed provide a default database and ORM for you, but it's not configured
by default, so you need configure it first. So if you don't like the ORM provided
by Uliweb, you can easily change it. Uliweb provide a plugin mechanism, it lets you
can add some initialization code when you need. Open ``GuestBook/settings.py`` file,
you can see something already existed:

.. code:: python

    from uliweb.core.plugin import plugin
    
``plugin`` is a decorator too, just like ``expose``, you can use it to decorate a function,
so it'll bind the function to a invoke point, and when the program runs at this
point, Uliweb will execute all the plugin functions one bye one. Ok, let's add
below code:

.. code:: python

    connection = {'connection':'sqlite://database.db'}
    #connection = {'connection':'mysql://root:limodou@localhost/test'}
    
    DEBUG_LOG = True
    
    @plugin('prepare_template_env')
    def prepare_template_env(sender, env):
        from uliweb.utils.textconvert import text2html
        env['text2html'] = text2html
        
    @plugin('startup')
    def startup(sender):
        from uliweb import orm
        orm.set_debug_log(DEBUG_LOG)
        orm.set_auto_bind(True)
        orm.set_auto_migirate(True)
        orm.get_connection(**connection)
        
Let me explain it bit by bit.

Connection String of Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``connection`` is used for database connection configure, it's a dict variable. 
The key ``connection`` is must, it the connection string of some database.
If there are some arguments which are difficult to write in ``connection`` string,
you can add them in the dict variable.

Here, we use sqlite database, and if you want to use MySql, you can write like 
the comment line.

A connection string format looks like

::

    provider://username:password@localhost:port/dbname?argu1=value1&argu2=value2
    
Some arguments can be default or organized in the ``connection`` dict variable. 
For example:

.. code:: python

    connection = {'connection':'mysql://localhost/test',
        'username':'limodou',
        'password':'password'}
    connection = {'connection':'mysql://localhost/test?username=limodou&password=password'}
    connection = {'connection':'mysql://limodou:password@localhost/test'}
    
Above three formats are all the same effect. If there are some arguments doesn't
provided, e.g. ``port`` argument, it'll use default value. For sqlite database,
because there is no username and password, so you can directly write it as:

.. code:: python
    
    connection = {'connection':'sqlite'}    #Memory database
    connection = {'connection':'sqlite://'} #Memory database
    connection = {'connection':'sqlite'://path'}    #Using file
    
The former two formats are the same. And the later will use file, you can use
absolute path or relative path.
    
Initialize Database
~~~~~~~~~~~~~~~~~~~~~~~

Uliweb will not do it for you, you should do it yourself. But if you choice Uliorm
(Uliweb ORM module), it's easy for you. Here we'll use Uliorm.

First we can set ``DEBUG_LOG = True``, notice that the ``DEBUG_LOG`` should be upper 
case. And if you set it, the underlying Sql statements will be outputed in the console,
so you can see if the Sql is what you want.

Then:

.. code:: python

    @plugin('startup')
    def startup(sender):
        from uliweb import orm
        orm.set_debug_log(DEBUG_LOG)
        orm.set_auto_bind(True)
        orm.set_auto_migirate(True)
        orm.get_connection(**connection)

When Uliweb executing at the position of ``startup``, it'll invoke all matched
plugin functions one by one. ``startup`` is a name of plugin invoking point,
and it's already defined in SimpleFrame.py, when Uliweb starting, the ``startup`` will
be invoked. Here ``sender`` is exactly the framework instance. The first argument 
of each plugin function is always the caller object.

Then it's the database initialization process. Because Uliweb will automatically
find and import each ``settings.py`` in every app directory, so you can write
initialization code an any app ``settings.py`` file, but I suggest you put it in 
your main app of your project.

``set_debug_log(DEBUG_LOG)`` will enable Uliweb output SQL statements in console when
running.

``set_auto_bind(True)`` will enable automatically binding setting. So when you 
import a Model, it'll be bound to default database connection, and you can use
it directly. Otherwise, you need manully bind each table to database connection.

``set_auto_migirate(True)`` will enable automatically table migirate process. It's
very useful. Firstly, if when you startup Uliweb and the table is not existed
in database yet, Uliweb will automatically create this table for you. Secondly,
it'll automatically check the Model structure and table structure, adding or
deleting fields automatically. So you don't need to change the table structure
manually. But it can't find out renaming field, just delete old field and add
new field, so this will make some data lost. So you should use it carefully.

Through above two steps, you can use Uliorm easily in Uliweb, just define it,
then use it. Working like create table, change table structure will be finished
automatically, it's very simple.

``orm.get_connection(**connection)`` will create database connection, and it'll 
do initialization works according above settings. So above settings need to be
done before you invoke get_connection() function. After creating database connection,
it'll set this connection object as global defult connection object.

Template Environment Extension
---------------------------------

There is other thing in settings.py

.. code:: python

    @plugin('prepare_template_env')
    def prepare_template_env(sender, env):
        from uliweb.utils.textconvert import text2html
        env['text2html'] = text2html

This is also a plugin usage example, it'll inject a new template function 
``text2html`` into template environment, so you can use it directly in template.
And this process will be available for global scope, so you can also use ``text2html``
in other apps.

``text2html`` can be used to convert plain text to HTML code, including hyperlink
process. This is written by me when I developing web application in Django before.

Prepare Model
----------------

Creating a ``models.py`` file in GuestBook directory, and add below code:

.. code:: python

    from uliweb.orm import *
    import datetime
    
    class Note(Model):
        username = Field(str)
        message = Field(str, max_length=1024)
        homepage = Field(str)
        email = Field(str)
        datetime = Field(datetime.datetime)
        
It's easy now, right?

First, you should import something from ``uliweb.orm``.

Then, you need to import datetime module. Why you need it? Because Uliorm
supports two ways to define field:

* One way is using internal Python data type, e.g. int, float, unicode,
  datetime.datetime, datetime.date, datetime.time, decimal.Decimal, str, bool, etc.
  And I also extend some other types, such as: blob, text.

  So you can use Python data type directly.

* The other way is using any Property class just like GAE, e.g. StringProperty, UnicodeProperty,
  IntegerProperty, BlobProperty, BooleanProperty, DateProperty, DateTimeProperty,
  TimeProperty, DecimalProperty, FloatProperty, TextProperty.

You should define your own model, and it should be inherited from ``Model`` class.
Then you can define fields which you want to use. There is a handy function named
``Field()``, you can pass it a Python data type, it'll automatically find a suit
Property class for you.

.. code:: python

    class Note(Model):
        username = StringProperty()
        message = TextProperty(max_length=1024)
        homepage = StringProperty()
        email = StringProperty()
        datetime = DateTimeProperty()
        
Each field may also has other arguments, for example:

* default
* max_length
* verbose_name 

etc. 

.. note::

    When you define Model class, Uliorm will automatically add a ``id`` field for
    you, it'll be a primary key.
    
Static Files Serving
-----------------------

If you open ``views.py`` in ``GuestBook`` directory, there should has some code:

.. code:: python

    #coding=utf-8
    from uliweb.core.SimpleFrame import expose
    
    @expose('/')
    def index():
        return '<h1>Hello, Uliweb</h1>'
    
Delete no usefule index() first, just keep the first two line.

Then add static file serving code:

.. code:: python

    from uliweb.core.SimpleFrame import static_serve
    @expose('/static/<regex(".*$"):filename>')
    def static(filename):
        return static_serve(request, filename)

Uliweb has already provide static files serving support, so you can use it to 
serve static files directly, or you can use other web server(Like Apache)
to do that. Each app in Uliweb has its own static directory, the goal of it is
to make each app individual as possible as it can. If you let Uliweb to 
serve static file, it'll try to find matched file in current app's static
directory, if it found it'll return the file, if not found, it'll search in
other apps' static directory. And in order to reduce download the same file
again, it'll just the modification of files, and return 304 response code if no
changes at all. You can see this in console when you use develop server.

Above expose uses regular expression, you can find more detail in `URL Mapping <url_mapping>`_
document.

Display Comments
-----------------------

Add guestbook() function to view
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open ``views.py`` in ``GuestBook`` directory, and add displaying comments code:

.. code:: python

    @expose('/guestbook')
    def guestbook():
        from models import Note
        
        notes = Note.filter(order=lambda z: [reversed(z.datetime)])
        return locals()

Here we define the ULR is ``/guestbook`` .

Then we define ``guestbook()`` function.

In function, we import ``Note`` class, then get all comments via its ``filter()`` 
method. In order to display the comments descend, we add a lambda function to 
``order`` argument. This is genuisql query expression usage, just a Python 
expression. It means that sorting the table ``z`` via ``datatime`` field in 
descend order. And ``reversed`` is a builtin function of Python.

Here are some simple usages:

.. code:: python

    notes = Note.filter()               #Gain all records, with no condition
    note = Note.get(3)                  #Gain records with id equals 3
    note = Note.get(username='limodou') #Gain records with username equals 'limodou'
    
Then we'll return locals() (locals() will return a dict variable, it's
easy then return {'a':1} format). Remember, when you return a dict variable,
Uliweb will automatically find a matched template to render the HTML page.

.. note::

    In Uliweb, every visit URL should be bound to a view function. Using ``expose``
    you should pass a URL to it, and it'll bind this URL to below function. And it'll
    convert a view function object to a string format, just like:
    
    ::
    
        apps.appname.viewmodule.functioname
        
    And Uliweb also provides a reversed URL creating function - url_for, you can 
    use it to create a URL according view function string like above format. We
    will see its usage in template later.

Create guestbook.html Template File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``guestbook.html`` file in ``GuestBook/templates`` directory, it's main filename
should be the same with ``guestbook()`` function. And add below code to it:

.. code:: django+html

    {{extend "base.html"}}
    <h1>Uliweb Guest Book</h1>
    <h2><a href="{{=url_for('%s.views.new_comment' % request.appname)}}">New Comment</a></h2>
    {{for n in notes:}}
    <div class="message">
    <h3><a href="/guestbook/delete/{{=n.id}}"><img src="/static/delete.gif"/></a> 
    {{=n.username}} at {{=n.datetime}} say:</h3>
    <p>{{=text2html(n.message)}}</p>
    </div>
    {{pass}}
    
The first line means this template will inherit from ``base.html``. I don't want to 
say so much about it, you just need to notice in ``base.html`` should has a 
``{{include}}`` in it, it means the child template insertion position will be there.
You can copy base.html from ``apps/GuestBook/templates`` to ``yourproject/apps/GuestBook/templates`` 
directory.

h2 tag will display an URL, this URL will link to add comment view function. 
Notice that I didn't put the display code with add comment Form code together,
because the code will be much in that way. And if there are some errors when
user input the comment, it'll display all comments again, so the process will
be slow, so I separate them into different processes.

``{{for}}`` is a loop. Remember Uliweb uses web2py template module, but makes some
improvements. The code between {{}} can be any Python code, so they should
follow the Python syntax. Thus, the ``:`` at the end of line can't be omitted.
You can also put html code in {{}}, but can't use them directly, you should
output them using ``out.write(htmlcode)``. When the block is ended, don't forget
to add a ``{{pass}}`` statement. And you don't need to worry about the indent,
Uliweb will reindent for you, as long as you add the correct pass statement.

In loop, it'll process the notes object, and then display a delete link, and 
then user info and user comments.

Have you seen ``{{=text2html(n.message)}}``? It uses ``text2html`` function which we
defined in settings.py to convert plain text to html code.

``{{pass}}`` is must.

Good, after above working, display comments is finished. But for now, you can
add comment yet, so let's see how to adding comment.

.. note::

    Because there are some CSS and image files used in base.html and guestbook.html,
    so you can copy them from Uliweb source directory to your project.
    
Add comment
--------------

Add new_comment() function to view
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the guestbook.htmk, we've already add some code to create add comment URL:

.. code:: html

    <a href="{{=url_for('%s.views.new_comment' % request.appname)}}">New Comment</a>
    
You can see, I use ``url_for`` to create reversed URL. ``url_for`` we've covered before,
the only thing you need notice here is the function named ``new_comment``, so we 
need to create such function in views.py.

Open the views.py file, and add below code:

.. code:: python

    @expose('/guestbook/new_comment')
    def new_comment():
        from models import Note
        from forms import NoteForm
        import datetime
        
        form = NoteForm()
        if request.method == 'GET':
            return {'form':form.html(), 'message':''}
        elif request.method == 'POST':
            flag, data = form.validate(request.params)
            if flag:
                data['datetime'] = datetime.datetime.now()
                n = Note(**data)
                n.put()
                redirect(url_for('%s.views.guestbook' % request.appname))
            else:
                message = "There is something wrong! Please fix them."
                return {'form':form.html(request.params, data, py=False), 'message':message}

The URL will be ``/guestbook/new_comment`` for ``new_comment()`` function.

First, we import some class, including ``Note`` Model. So what's NoteForm? It's a
form class, we can use it to validate data, and even output HTML form code. I'll
introduce it later.

Then creating an instance from NoteForm.

According to ``request.method`` is ``GET`` or ``POST``, we can decide to execute different
process. For GET method, I'll display an empty Form, for POST method, it means
user has submitted data, need to process. Through judging GET or POST, you can 
do different process under the same URL, for GET, means read operation, for
POST, means write operation.

If the ``request.method`` is ``GET``, we just return empty form HTML code, and 
empty message variable. ``form.html()`` can return empty form html code, while
message will be used for display error message.

If the ``request.method`` is ``POST``, we'll invoke ``form.validate(request.params)`` 
to validate submitted data by user. It'll return two element tuple, and first is
result flag, means success or fail, second will be the converted Python data or 
error messages according to the result flag.

当flag为True时，进行成功处理。一会我们可以看到在表单中并没有datetime字段，因此这里我们
手工添加一个值，表示留言提交的时间。然后通过 ``n = Note(**data)``` 来生成Note记录，但这里并没有提
交到数据库中，因此再执行一个 ``n.put()`` 来保存记录到数据库中。使用 ``n.save()`` 也可以。

然后执行完毕后，调用 ``redirect`` 进行页面的跳转，跳回留言板的首页。这里又使用了url_for来反
向生成链接。注意redirect前不需要有 ``return`` 。
    
当flag为False时，进行出错处理。这里我们向message中填入了出错提示，然后通过
``form.html(request.params, data, py=False)`` 来生成带出错信息的表单。这里data为出错
信息。 ``py=False`` 是表示在使用数据时不进行Python数据转换。因为Form在校验数据之后会根据
你所定义的数据类型，将上传的数据转换为Python的内部数据，如：int, float之类的。但是当出错
时，不存在转换后的Python数据，因此不能做这种转换，这时要使用 ``py=False`` 参数。如果data
是校验成功的数据，你想通过表单显示出来，可以直接使用 ``form.html(data)`` 就可以了。

定义录入表单
~~~~~~~~~~~~~

为了与后台进行交互，让用户可以通过浏览器进行数据录入，需要使用HTML的form系列元素来定义
录入元素。对于有经验的Web开发者可以直接手写HTML代码，但是对于初学者很麻烦。并且你还要考虑
出错处理，数据格式转换的处理。因此许多框架都提供了生成表单的工具，Uliweb也不例外。Form模
块就是干这个用的。

在GuestBook目录下创建forms.py文件，然后添加以下代码：

.. code:: python

    from uliweb.core import Form
    
    Form.Form.layout_class = Form.CSSLayout
    
    class NoteForm(Form.Form):
        message = Form.TextAreaField(label='Message:', required=True)
        username = Form.TextField(label='Username:', required=True)
        homepage = Form.TextField(label='Homepage:')
        email = Form.TextField(label='Email:')

首先导入Form模块，然后设定Form类使用css布局。目前Uliweb的Form提供两种布局，一种是使用
table元素生成的，另一种是使用div元素生成的。table布局是缺省的。

接着就是创建NoteForm元素了。这里我定义了4个字段，每个字段对应一种类型。象TextAreaField
表示多行的文本编辑，TextField表示单行文本，你还可以使用象：HiddenField, SelectField,
FieldField, IntField, PasswordField, RadioSelectField等字段类型。目前Form的定义方式
与Uliorm的不太一致，因为Form创建的时间更早，以后也可以考虑写一个统一的Field来进行一致性
的处理。

也许你看到了，这其中有一些是带有类型的，如IntField，那么它将会转换为对应的Python数据类
型，同时当生成HTML代码时再转换回字符串。

每个Field类型可以定义若干的参数，如：

* label 用来显示一个标签
* required 用来校验是否输入，即不允许为空
* default 缺省值
* validators 校验器

很象Model的定义，但有所不同。

编写new_comment.html模板文件
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在GuestBook/templates下创建new_comment.html，然后添加以下内容：

.. code:: html

    {{extend "base.html"}}
    {{if message:}}
    <p class="message">{{=message}}</p>
    {{pass}}
    <h1>New Comment</h1>
    <div class="form">
    {{Xml(form)}}
    </div>

首先是 ``{{extend "base.html"}}`` 表示从base.html继承。

然后是一个 if 判断是否有message信息，如果有则显示。这里要注意if后面的':'号。

然后显示form元素，这里使用了 ``{{Xml(form)}}`` 。form是从View中传入的，而Xml()是模板中
的内置方法，它用来原样输出内容，对HTML的标签不会进行转换。而 {{=variable}} 将对variable
变量的HTML标签进行转换。因此，如果你想输出原始的HTML文本，要使用Xml()来输出。

现在可以在浏览器中试一下了。

删除留言
----------

在前面guestbook.html中，我们在每条留言前定义了一个删除的图形链接，形式为：

.. code::

    <a href="/guestbook/delete/{{=n.id}}"><img src="/static/delete.gif"/></a>
    
那么下面就让我们实现它。

打开GuestBook/views.py文件，然后添加：

.. code:: python

    @expose('/guestbook/delete/<id>')
    def del_comment(id):
        from models import Note
    
        n = Note.get(int(id))
        if n:
            n.delete()
            redirect(url_for('%s.views.guestbook' % request.appname))
        else:
            error("No such record [%s] existed" % id)

删除很简单，导入Note，然后通过 ``Note.get(int(id))`` 来得到对象，然后再调用对象的delete()
方法来删除。

URL参数定义
~~~~~~~~~~~~

请注意，这里expose使用了一个参数，即 ``<id>`` 形式。一旦在expose中的url定义
中有<type:para>的形式，就表示定义了一个参数。其中type:可以省略，它可以是int等类型。而
int将自动转化为 ``\d+`` 这种形式的正则式。Uliweb内置了象: int, float, path, any, string,
regex等类型。如果只是 ``<name>`` 则表示匹配 //　间的内容。一旦在URL中定义了参数，则需要
在View函数中也需要定义相应的参数，因此del_comment函数就写为了： ``del_comment(id)`` 。
这里的id与URL中的id是一样的。

好了，现在你可以试一试删除功能是否可用了。

出错页面
~~~~~~~~~~~~~~~~

当程序出错时，你可能需要向用户提示一个错误信息，因此可以使用error()方法来返回一个出错
的页面。它的前面不需要return。只需要一个出错信息就可以了。

那么出错信息的模板怎么定义呢？在你的templates目录下定义一个名为error.html的文件，并加
入一些内容即可。

创建error.html，然后，输入如下代码：

.. code:: html

    {{title="Error"}}
    {{extend "base.html"}}
    <h1>Error!</h1>
    <p>{{=message}}</p>


这个页面很简单，就是定义了一个title变量，然后是继承base.html，再接着是显示出错内容。

不过这里有一个很重要的技巧，那就是在 {{extend}} 前面定义的内容在渲染模板时，将出现在最
前面。这样，一旦父模板中有一些变量需要处理，但是你没有通过View方法来传入，而是在子模板
中来定义它，通过这种方法就可以将定义放在使用语句的前面，从而不会报未定义的错误。

.. note::

    这是我对web2py模板的一个扩展。以前web2py要求{{extend}}是第一行的，但现在可以不是。
    并且这种处理可以很好的处理：在子模板中定义在父模板中要使用的变量的情况。
    
运行
------

在前面的开发过程中你可以启动一个开发服务器进行调试。启动开发服务器的命令为：

::

    python manage.py runserver
    
当启动后，在浏览器输入： ``http://localhost:8000/guestbook``

注意，这里不是从/开始的。
    
结论
-------

经过学习，我们了解了许多内容：

#. ORM的使用，包括：ORM的初始化配置，Model的定义，简单的增加，删除，查询
#. Form使用，包括：Form的定义，Form的布局，HTML代码生成，数据校验，出错处理
#. 模板的使用，包括： {{extend}} 的使用，在模板环境中增加自定义函数，子模板变量定义的
   技巧，错误模板的使用，Python代码的嵌入
#. View的使用，包括：redirect, error的使用, 静态文件处理
#. URL映射的使用，包括：expose的使用，参数定义，与View函数的对应
#. manage.py的使用，包括：export, makeapp的使用
#. 结构的了解，包括：Uliweb的app组织，settings.py文件的处理机制，view函数与模板文件
   的对应关系

内容很多，的确。而这些还远远不是一个框架的全部。随着应用的复杂，框架的功能也会越来越多。
而一个好的框架应该就是让有经验的人用来首先构建出一个更易于使用，易于管理的环境，然后
让团队中的人在这个环境下去开发，让对框架有经验的人对环境进行不断的调整和完善，使其越来
越方便和强大。Uliweb正在向着这个目标前进。