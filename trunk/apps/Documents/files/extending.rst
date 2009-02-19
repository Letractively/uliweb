Extending Uliweb
=================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

A web framework might fall short to anticipate all your development needs. 
Although Uliweb is no exemption in this respect, it strives to provide the most 
possible amount of flexibility and extensibility.

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

You can also define the arguments used in an invocation point, for example:

.. code:: python

    callplugin(self, 'startup_installed')
    
All invocation points are just functions, the first argument must be the sender
object and other arguments might follow. And there is a special argument
``signal``, this can be a simple type, for example, ``None``, or a string. If the 
invoking point set to this argument, a plugin function can match or skip it, 
depending on how your plugin function is defined.

There are four kinds of plugin invocation function:

* callplugin Can't be interrupted and will return nothing, can be executed several times
* callplugin_once Just like above, but can only be executed once
* execplugin Can be interrupted and will return a value(if any plugin function
  returns a value that is not ``None``, the execution will be interrupted)
* execplugin_once Just like above, but can only be executed once, and if it is invoked
  a second time, it'll return the first return value.

**Plugin collection system** is used the collect all plugin functions. This works in the sense that  
when the Uliweb main process execution reaches an invocation point, it'll look for matching plugin
functions in from the collection system to execute. The most suitable places to define plugins are in
each app's ``__init__.py`` or app's ``start.py``, because they'll 
be imported automatically when the Uliweb started.
