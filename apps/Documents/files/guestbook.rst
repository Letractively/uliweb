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
of each plugin function is always the caller object. Here is the application instance
object.

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
    
Delete no useful index() first, just keep the first two lines.

Then add static file serving code:

.. code:: python

    from uliweb.core.SimpleFrame import static_serve
    @expose('/static/<path:filename>')
    def static(filename):
        return static_serve(request, filename)

Uliweb has already provided static files serving support, so you can use it to 
serve static files directly, or you can use other web server(Like Apache)
to do that. Each app in Uliweb has its own static directory, the goal of it is
to make each app individual as possible as it can. If you let Uliweb to 
serve static files, it'll try to find matched file in current app's static
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

When the flag is ``True``, it means the validation is successful. We can
see there is no ``datetime`` field, so we add it manually, it'll be used for the submited
datetime of the comment. Then we can invoke ``n = Note(**data)`` to create a new
Note record, but we have not commit it to the database yet, so we can invoke
``n.put()`` to store the record to the database. You can also use ``n.save()`` to 
store the record, it's the same.

After that, we will invoke ``redirect`` to jump another page, it's the homepage of
GuestBook. Here we use ``url_for`` again to create reversed URL. Notice you don't
need to write return before it.
    
If the flag is ``False``, it means validation is failed. So we assign an error message
to ``message`` variable, then invoke ``form.html(request.params, data, py=False)`` 
to create a form with error message. And data is the error details of each 
field. ``py=False`` means we will use submitted data directly but not Python
data. Because if the validation is failed,  the valid Python data has not 
existed yet. If you want to render valid Python data, you can just use
``form.html(data)``.

Define Form
~~~~~~~~~~~~~

In order to interact with server, uesr can through browser to input data,
so you should provide Form HTML element to receive the input. For an experienced
web developer, he can write HTML code manually, but it's difficult for newbies.
And you should also think about how to deal with error, data format conversion, etc.
So many frameworks supply such Form helper tool, Uliweb also provides such thing.
The Form module will be used for this.

Creating a ``forms.py`` file in ``GuestBook`` directory, then add below code:

.. code:: python

    from uliweb.core import Form
    
    Form.Form.layout_class = Form.CSSLayout
    
    class NoteForm(Form.Form):
        message = Form.TextAreaField(label='Message:', required=True)
        username = Form.TextField(label='Username:', required=True)
        homepage = Form.TextField(label='Homepage:')
        email = Form.TextField(label='Email:')

First, importing ``Form`` module, then set CSSLayout. For now, Uliweb supports two
form layout, one it table layout which uses ``table`` tag, the other is css layout
which uses ``div`` tag. And table layout is default.

Then, we'll create NoteForm class, here I define 4 fields, each field maps a 
type. For example, TextAreaField means multilines text input, TextField means
single line text input, and you can also use: HiddenField, SelectField,
FileField, IntField, PasswordField, RadioSelectField, etc. 

Maybe you've seen that, some of these fields have type, e.g. IntField, so it'll
be automatically convert submitted data to Python data type, and convert back
when creating HTML code.

Each field may has some arguments, for example:

* label used to display a label tag
* required if a field can't be empty
* default default vallue
* validators used to validate the data

It likes the definition of Model, but they are different.

Create new_comment.html Template File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creating a ``new_comment.html`` file in ``GuestBook/templates`` directory, then add beclow code:

.. code:: html

    {{extend "base.html"}}
    {{if message:}}
    <p class="message">{{=message}}</p>
    {{pass}}
    <h1>New Comment</h1>
    <div class="form">
    {{Xml(form)}}
    </div>

First line is ``{{extend "base.html"}}``, it means that you'll extend from ``base.html``
template file.

Then it's a if statement, it'll test if the message is not empty, if not, then
display it. Notice the ``:`` at the end of the line.

Then display form element, here I used ``{{Xml(form)}}``. ``form`` is passwd from view
function, but ``Xml()`` is a builtin function define in template system, you can 
use it directly, it'll output the code directly without any escape process.
For ``{{= variable}}`` will escape the output, it'll convert HTML tag to HTML entities.
So if you don't want the output be escaped, you should use ``Xml()``.

Now, you can try current work in the browser.

Delete Comment
---------------

In ``guestbook.html``, we defined a link which will be used to delete comment, the format
is:

.. code::

    <a href="/guestbook/delete/{{=n.id}}"><img src="/static/delete.gif"/></a>
    
So let's implement it.

Open ``GuestBook/views.py`` file, and append below code:

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

Delete is simple, just import Note model, then invoke ``Note.get(int(id))`` to 
get the object, next invoke ``delete()`` function of object to delete the record.

URL Arguments Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Notice, here, expose() uses an argument, i.e. ``<id>``. Once there are something 
like ``<type:para>`` in the URL, that's means you defined an argument. And ``type``
can be optional. Uliweb provides many builtin types, such as: int, float, path,
any, string, uniocde. And you can find more details in `URL Mapping <url_mapping>`_
document. If you just define ``<name>`` format, it just means matching something 
between ``//``. Once you defined some arguments in the URL, you must define the
same arguments in the view function, so ``del_comment()`` function should be written
in ``del_command(id)``. There the ``id`` arugment is the same as the one in URL.

Ok, now you can try if the delete function can be used.

Error Page
~~~~~~~~~~~~~~~~

When there are something wrong, you may need to show an error page to user, so
you can use ``error()`` function to return an error page. ``return`` is no need in front
of it, just give it an error message, that's enough.

How to create error template file? Just create a file named ``error.html`` in
your app templates directory, and add something like:

.. code:: html

    {{title="Error"}}
    {{extend "base.html"}}
    <h1>Error!</h1>
    <p>{{=message}}</p>


It's simple right, we just define a ``title`` variable and then extend the ``base.html``,
then output the message.

But here is an imortant trick, that's if you write something before ``{{extend}}``,
these things will be placed at the top of the template rendering output. So 
if there are some variables used in parent template, but you didn't pass them
through view funcion, however define them in child template, by this trick,
you can put the variables definition in front of the using statements, and 
this will not cause syntax error.

.. note::

    This is my extension for web2py template system. In the past, web2py requires
    ``{{extend}}`` should be the first statement, but for now, you can put something
    in front of it. This way can easy deal with defining variable in child tamplte.
    
Run
------

In previous developing process, you can also start a developing server to test
your project. The command of starting a developing server is:

::

    python manage.py runserver
    
When it starting, you can input ``http://localhost:8000/guestbook`` to test this
GuestBook demo.

Notice, here is not begin with ``/``.
    
Conclusion
-------------

Wow, we've learnt so much things for now:

#. ORM usage, including: ORM initilization, Model definition, simple add, delete, qurry.
#. Form usage, including: Form definition, Form layout, HTML creation, data validation, error process.
#. Template usage, including: {{extend}} usage, add custom variables to template.
   environment, define variables in child template, write Python code in template.
#. View usage, including: redirect usage, error usage, static files serving.
#. URL mapping usage, including: expose usage, arguments definition.
#. manage.py usage, including: export and makeapp usage.
#. Architecture knowledge, inclueing: the organization of Uliweb, settings process.
   flow mechanism, the mapping between view function and template file.

Yes, there are too much things. However these are not the whole stuff of Uliewb yet.
Along with the application becomes more complex, the functionalities of frameworks
will be more and more. But I think a good framework should enable experienced 
developers build an environment which should be easy to use and easy to manage,
then the others of this team could work under this environment,
and the duty of those expericenced developers should to change to make this environment better
and powerful. I hope Uliweb can step foward to this goal.