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
    def startup(sender, config, *args):
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
    def startup(sender, config, *args):
        from uliweb import orm
        orm.set_debug_log(DEBUG_LOG)
        orm.set_auto_bind(True)
        orm.set_auto_migirate(True)
        orm.get_connection(**connection)

When Uliweb executing at the position of ``startup``, it'll invoke all matched
plugin functions one by one. ``startup`` is a name of plugin invoking point,
and it's already defined in SimpleFrame.py, when Uliweb starting, the ``startup`` will
be invoked. Using ``*args`` here is in order to extend for later. Here ``sender`` is
exactly the framework instance. The first argument of each plugin function
is always the caller object.

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

    在Uliweb中每个访问的URL与View之间要通过定义来实现，如使用expose。它需要一个URL的
    参数，然后在运行时，会把这个URL与所修饰的View方法进行对应，View方法将转化为：
    
        appname.viewmodule.functioname
        
    的形式。它将是一个字符串。然后同时Uliweb还提供了一个反向函数url_for，它将用来根据
    View方法的字符串形式和对应的参数来反向生成URL，可以用来生成链接，在后面的模板中我
    们将看到。

Create guestbook.html Template File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在GuestBook/templates目录下创建与View方法同名的模板，后缀为.html。在guestbook.html中
添加如下内容：

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
    
第一行将从base.html模板进行继承。这里不想多说，只是要注意在base.html中有一个{{include}}
的定义，它表示子模板要插入的位置。你可以从Uliweb的源码中将base.html拷贝到你的目录下。

h2 显示一个标准。并且是一个链接，它连接到添加留言的URL上去了。注意模板没有将显示与添加的
Form写在一起，因为那样代码比较多，同且如果用户输入出错，将再次显示所有的留言(因为这里
没有考虑分页)，这样处理比较慢，所以分成不同的处理了。

``{{for}}`` 是一个循环。记住Uliweb使用的是web2py的模板，不过进行了改造。所有在{{}}中的代码
可以是任意的Python代码，所以要注意符合Python的语法。因此后面的':'是不能省的。Uliweb的模
板允许你将代码都写在{{}}中，但对于HTML代码因为不是Python代码，要使用 ``out.write(htmlcode)`` 
这种代码来输出。也可以将Python代码写在{{}}中，而HTML代码放在括号外面，就象上面所做的。

在循环中对notes变量进行处理，然后显示一个删除的图形链接，用户信息和用户留言。

看到 ``{{=text2html(n.message)}}`` 了吗？它使用了我们在settings.py中定义的text2html函
数对文本进行格式化处理。

``{{pass}}`` 是必须的。在Uliweb模板中，不需要考虑缩近，但是需要在块语句结束时添加pass，表示缩
近结果。这样相当于把Python对缩近的严格要求进行了转换，非常方便。

好，在经过上面的工作后，显示留言的工作就完成了。但是目前还不能添加留言，下一步就让我们看如
何添加留言。

.. note::

    因为在base.html中和guestbook.html用到了一些css和图形文件，因此你可以从Uliweb的
    GuestBook/static目录下将全部文件拷贝到你的目录下。
    
增加留言
----------

增加new_comment()的View方法
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在前面的模板中我们定义了增加留言的链接：

.. code:: html

    <a href="{{=url_for('%s.views.new_comment' % request.appname)}}">New Comment</a>
    
可以看出，我们使用了url_for来生成反向的链接。关于url_for在前面已经讲了，这里要注意的就是
函数名为new_comment，因此我们需要在views.py中生成这样的一个方法。

打开views.py，加入以下代码：

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

可以看到链接是 ``/guestbook/new_comment`` 。

首先我们导入了一些模板，包括Note这个Model。那么NoteForm是什么呢？它是用来生成录入Form的
对象，并且可以用来对数据进行校验。一会儿会对它进行介绍。

然后创建form对象。

再根据request.method是GET还是POST来执行不同的操作。对于GET将显示一个空Form，对于POST
表示用户提交了数据，要进行处理。使用GET和POST可以在同一个链接下处理不同的动作，这是一种
约定，一般中读操作使用GET，写或修改操作使用POST。

在request.method为GET时，我们只是返回空的form对象和一个空的message变量。form.html()可
以返回一个空的HTML表单代码。而message将用来提示出错的信息。

在request.method为POST时， 首先调用 ``form.validate(request.params)`` 对数据进行校验。
它将返回一个二元的tuple。第一个参数表示成功还是出错，第二个为成功时将转换为Python格式后
的数据，失败时为出错信息。

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