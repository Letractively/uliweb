Form
================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

Form creating and processing is a big problem in web development. Uliweb provides
its own Form process module, it's just named ``Form`` in uliweb/core directory.
But it's not bound by default, it's just a common Python module, so you should
import it when you want to use it. So it also means that you can use other Form module
in Uliweb.

What's the feature of the Form module in Uliweb?

* Define it just like define a model
* Creating HTML code directly from Field, Form object
* Support layout process, so you can define your own HTML output
* Can validate the submitted data and convert them into Python data type
* Support user defined validator
* Provide a form app(not implemented yet), so you can use it more easier

Form class
------------

If you want to use Form module, you should define a Form class first, just like
this:

.. code:: python

    from uliweb.form import *

    class Form1(Form):
        title = TextField(label='Title:', required=True, help_string='Title help string')
        content = TextAreaField(label='Content:')

You can see, you should inherit from ``Form`` class, and you can define field directly
in Form class, just like define class attributes.

Then you could create Form object, just like:

.. code:: python

    f = Form1()
    
When creating Form instance, there are some parameters you can set:

    action
        It's the ``action`` attribute of <form> tag, if not set it, it'll be ``""``.
        
    method
        It's the ``method`` attribute of <form> tag, if not set it, it'll be ``post``.
        
    buttons
        It'll be used to create button lines of a form, like submit and reset button.
        If you not set it, default will be submit and reset buttons. The HTML code
        will be:
        
        .. code:: html
        
            <input type="submit" value="Submit"></input>
            <input type="reset" value="Reset"></input>
            
        If you want other buttons, you can provide any HTML code in ``buttons`` 
        parameter, Form will use it to create buttons.

    validators
        User can write Form level validators, it should be a list of validators.
        More details about validator you can see *Validator* section below.
        
    html_attrs
        Other attributes you can set to form tag.
        
    data
        Data you want to set. It should be a dict, each key will be the attribute
        name. If you set it, it'll be replace with default value of matched field.
        You don't need to set it in initialization, you can use Form.binding() 
        or when you call Form.check() to validate the submit data, the errors 
        will be automatically bound.
        
    errors
        Error message of each field or the global error. It's a dict too. And if
        the key is ``'_'`` it means it's global error. You don't need to set it in 
        initialization, you can use Form.binding() or when you call Form.check()
        to validate the submit data, the errors will be automatically bound.
        
    idtype
        idtype is used to indicate how to create ``id`` attribute. Default is ``'name'``,
        that means when creating HTML code for a field, it'll use the field name
        as the ``id`` value, the format will be ``field_<fieldname>``. If it's ``None``,
        the created HTML code will not has ``id`` attribute at all. And if it's other
        value the id format will be ``field_<no>``, each field will have a unique
        id number value when creating the instance.
        
Defining a Form
------------------

You can define any field as you want in a Form class, just define it in Form class
just like abvoe example. More details about available fields you can see *Bultin
Fields* section.

Beside defining fields in a Form class, you can also define validators for fields
or whole Form. For example:

.. code:: python

    from uliweb.form import *

    class F(Form):
        user_name = StringField(required=True)
        password = PasswordField(required=True)
        enter_password_again = PasswordField(required=True)
        
        def validate_user_name(self, data):
            if data != 'limodou':
                raise ValidationError, 'Username should be limodou'
            
        def validate(self, all_data):
            if all_data.password != all_data.enter_password_again:
                raise ValidationError, 'Passwords are not matched'

This example demenstrates how to define a validateor for ``user_name`` field in
the ``F`` form. You can define a function which name is like ``validate_<field_name>``.
And how to define a whole Form level validator, just define a function which
name is ``validate``.

Form Layout
--------------

Form class supports layout feature. A layout can be used to create real
HTML code. There are two layouts: TableLayout and CSSLayout already defined
in Form module. So you can use them directly. Default is TableLayout. And if you
want to change it, just define a ``layout_class`` attribute in Form class. 
For example:

.. code:: python

    from uliweb.form import *

    class F(Form):
        layout_class = CSSLayout
        
        title = StringField(label='Title:', required=True, help_string="This is a help string")
        date = DateField(label='Date:', name='adate', required=True)

Outputing HTML code
----------------------

For simple cases, you may want to output Form HTML code with empty value. For 
example, below is view function:

.. code:: python

    from uliweb.form import *

    @expose('/form_test')
    def form_test():
        class F(Form):
            user_name = StringField(required=True)
            password = PasswordField(required=True)
            enter_password_again = PasswordField(required=True)

        f = F()
        return {'form':f}
        
So after you create the instance of ``F``, you can return a dict to template. And
the template is:

.. code:: html

    {{ if '_' in form.errors: }}
    <h2>Error:{{=form.errors._}}</h2>
    {{pass}}
    {{<< form}}

For first 3 lines, they are the form level error display process. And ``{<< form}}``
is: outputing the form object withouth escaping, so characters like ``<`` etc. will
not be converted to ``&lt;``. That's exactly what we want.

If you want the form have initial values, you have two ways. One you can pass the
``data`` and ``errors``(if existing) parameters to Form initialization function. For
example:

.. code:: python

    from uliweb.form import *

    class F(Form):
        user_name = StringField(required=True)
        password = PasswordField(required=True)
        enter_password_again = PasswordField(required=True)
    
    d = {'user_name':'limodou'}
    f = F(data=d)
    
Or you can use Form.binding() function. For example:

.. code:: python

    f = F()
    f.binding(data=d)
    
.. note::

    The ``data`` should be a dict, and the values are matched with the Fields date
    type.