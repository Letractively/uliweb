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

There is already the whole GuestBook source code in Uliweb demos directory.
Just download the newest source code of Uliweb, then start developing server:

::

    cd demos/guestbook
    uliweb runserver
    
Enter http://localhost:8000/guestbook in the browser, then you'll find it.
By default, it'll use sqlite3, so if you are using Python 2.5, you'll not need
to install sqlite Python binding module. Or you need to install pysqlite2 package
yourself. For now, Uliweb uses `SqlAlchemy <http://www.sqlalchemy.org>`_ for 
underlying database driven module, it already supports many database, such as: 
mysql, sqlite, postgresql, etc. Before you want to use
other databases, you should also install their database module first.

Ok, let's begin to write code.

Create Project
----------------

I suggest that you begin your work in a new directory, for example: samples:

::

    uliweb makeproject guestbook
    
So it'll export all necessary Uliweb source code to outputdir directory. Then
goto this directory, ready to begin.

Create App
-----------

Goto the project directory built in previous step, and use ``makeapp`` to create a
new app.

::

    cd samples
    uliweb makeapp GuestBook
    
This will automatially create a ``GuestBook`` app for you in ``apps`` 
directory of your project.

Configure Database
--------------------

In this tutorial we'll use Uliweb orm to access database. And there is also
a builtin orm app, so that you can use it directly. Just editing ``guestbook/apps/settings.ini``,
then change the ``INSTALLED_APPS`` to::

    INSTALLED_APPS = [
        'GuestBook',
        'uliweb.contrib.orm',
        ]

Then add following content::

    [ORM]
    CONNECTION = 'sqlite:///guestbook.db'

So the ``settings.ini`` will look like::

    [GLOBAL]
    DEBUG = True
    
    INSTALLED_APPS = [
        'GuestBook',
        'uliweb.contrib.orm',
        ]
    
    [ORM]
    CONNECTION = 'sqlite:///guestbook.db'
    
ORM.CONNECTION is the connection string of orm, it's the same as SQLAlchemy package,
the generic format will look like::

    provider://username:password@localhost:port/dbname?argu1=value1&argu2=value2
    
For Sqlite, the conntection is somewhat different::
    
    sqlite_db = create_engine('sqlite:////absolute/path/to/database.txt')
    sqlite_db = create_engine('sqlite:///d:/absolute/path/to/database.txt')
    sqlite_db = create_engine('sqlite:///relative/path/to/database.txt')
    sqlite_db = create_engine('sqlite://')  # in-memory database
    sqlite_db = create_engine('sqlite://:memory:')  # the same
    
Here we use relative path format, so the ``guestbook.db`` will be created at guestbook
folder.
    
Template Environment Extension
---------------------------------

Because we want to enable user input plain text and output them as HTML code,
so we'll use uliweb.utils.text2html function to convert text to HTML code, and
we can indeed import this function in template file, but we can also hook
``prepare_template_env`` plugin, and inject a ``text2html`` function object to 
template environment, so that you can use ``text2html`` directly in template.
Open ``GuestBook/__init__.py`` and adding below codes:

.. code:: python

    from uliweb.core.plugin import plugin
    
    @plugin('prepare_template_env')
    def prepare_template_env(sender, env):
        from uliweb.utils.textconvert import text2html
        env['text2html'] = text2html

This is a plugin hook usage example, and there are some others plugin hook you can
use.

Prepare Model
----------------

Creating a ``models.py`` file in GuestBook directory, and add below code:

.. code:: python

    from uliweb.orm import *
    import datetime
    
    class Note(Model):
        username = Field(str)
        message = Field(text)
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
        message = TextProperty()
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

We'll need to display static files later, now we can just add ``uliweb.contrib.staticfiles``
to ``INSTALLE_APPS`` of ``settings.ini``. Using this app, all static directories of 
available apps will be processed as static folder, and the URL link will start
begin with ``/static/``. Now the ``settings.ini`` will look like::

    [GLOBAL]
    DEBUG = True
    
    INSTALLED_APPS = [
        'GuestBook',
        'uliweb.contrib.orm',
        'uliweb.contrib.staticfiles',
        ]
    
    [ORM]
    CONNECTION = 'sqlite:///guestbook.db'
    
Just a Test
---------------

Now we can test it. Just run the command line::

    uliweb runadmin
    
Then we can visit the http://localhost:8000 the result will be:

.. image:: /static/guestbook01.jpg

Display Comments
-----------------------

Add guestbook() function to view
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open ``views.py`` in ``GuestBook`` directory, and add displaying comments code:

.. code:: python

    @expose('/guestbook')
    def guestbook():
        from models import Note
        from sqlalchemy import desc
        
        notes = Note.filter(order_by=[desc(Note.c.datetime)])
        return locals()

Here we define the ULR is ``/guestbook`` .

Then we define ``guestbook()`` function.

In function, we import ``Note`` class, then get all comments via its ``filter()`` 
method. In order to display the comments descend, we add some condition to 
``order_by`` argument. This is SqlAlchemy query expression usage. 

Here are some simple usages:

.. code:: python

    notes = Note.all()               #Gain all records, with no condition
    note = Note.get(3)                  #Gain records with id equals 3
    note = Note.get(Note.c.username=='limodou') #Gain records with username equals 'limodou'
    
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
    {{block main}}
    <h1>Uliweb Guest Book</h1>
    <h2><a href="{{=url_for('%s.views.new_comment' % request.appname)}}">New Comment</a></h2>
    {{for n in notes:}}
        <div class="message">
        <h3><a href="{{= url_for('%s.views.del_comment' % request.appname, id=n.id) }}">
        <img src="{{= url_for_static('delete.gif') }}"/>
        </a> {{=n.username}} at {{=n.datetime.strftime('%Y/%m/%d %H:%M:%S')}} say:</h3>
        <p>{{=text2html(n.message)}}</p>
        </div>
    {{pass}}
    {{end}}
    
    
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
                n = Note(**data)
                n.put()
                return redirect(url_for('%s.views.guestbook' % request.appname))
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

After that, we will invoke ``return redirect`` to jump another page, it's the homepage of
GuestBook. Here we use ``url_for`` again to create reversed URL. 
    
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
    {{block main}}
    {{if message:}}
        <p class="message">{{=message}}</p>
    {{pass}}
    <h1>New Comment</h1>
    <div class="form">
    {{Xml(form)}}
    </div>
    {{end}}

First line is ``{{extend "base.html"}}``, it means that you'll extend from ``base.html``
template file.

Then it's a if statement, it'll test if the message is not empty, if not, then
display it. Notice the ``:`` at the end of the line.

Then display form element, here I used ``{{<<form}}``. ``form`` is passwd from view
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

    <a href="{{=url_for('%s.views.new_comment' % request.appname)}}">New Comment</a>
    
So let's implement it.

Open ``GuestBook/views.py`` file, and append below code:

.. code:: python

    @expose('/guestbook/delete/<id>')
    def del_comment(id):
        from models import Note
    
        n = Note.get(int(id))
        if n:
            n.delete()
            return redirect(url_for('%s.views.guestbook' % request.appname))
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
#. Architecture knowledge, including: the organization of Uliweb, settings process.
   flow mechanism, the mapping between view function and template file.

Yes, there are too much things. However these are not the whole stuff of Uliewb yet.
Along with the application becomes more complex, the functionalities of frameworks
will be more and more. But I think a good framework should enable experienced 
developers build an environment which should be easy to use and easy to manage,
then the others of this team could work under this environment,
and the duty of those expericenced developers should to change to make this environment better
and powerful. I hope Uliweb can step foward to this goal.