Extending Uliweb
=================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

It is very hard to anticipate all your needs, that is why Uliweb strives to 
provide a lot of flexibility and extensibility.

Plugin System
---------------

Uliweb provides a simple plugin system that consists of three components: plugin invocation points, 
the plugin collection system and the plugin processing functions. 

Each **Invocation point** will invoke all matching plugin functions, and each 
invoking point may have several matching plugins functions at a time. These functions can 
also be assigned execution priority attributes, this ensures that they will be sorted 
an executed according to a defined. There are two was that plugins are called 
when they encounter an invocation point, the first is the ``call`` method, this 
method invokes plugin functions one after the other, the process cannot be stopped 
in mid-execution, and it does not have a return value. The other method is called
 ``exec``, this method invokes plugin functions also one after the other, but with a difference,
, if any function returns a value other than ``None``, the execution will stop and the
value will be returned. So you can choose the suitable method that fits your needs.

You can also define the arguments used in this invoking point, for example:

.. code:: python

    callplugin(self, 'startup_installed')
    
All invoking points are just functions, the first argument must be the sender
object, and you can also use other arguments. And there is a special argument
``signal``, is can be just simple type, for example, ``None``, or a string. If the 
invoking point set this argument, plugin function can match it or just skip it,
it depends on how do you define your plugin function, will see it below.

There are four kinds of function:

* callplugin Can't be interrupted and will return nothing, can be executed many times
* callplugin_once Just like above, but can only be executed once
* execplugin Can be interrupted and will return a value(if any plugin function
  return a value is not ``None``, the execution will be interrupted)
* execplugin_once Just like above, but can only be executed once, and invoke
  it the next time, it'll return the first return value.

**Plugin collection system** is used the collect all plugin functions. 
When Uliweb execution reaches an invocation point, it'll look for a mtaching plugin
functions from the collection system. But you should define plugin function 
first. Which places are the mose suitable place to writing the plugin functions?
The answer is in each app's ``__init__.py`` or app's ``start.py``, because they'll 
be imported automatically when the Uliweb started.
