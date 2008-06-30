Extending Uliweb
=================

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

Every framework can't provide everything what you want, so the extending
ability is very important, and Uliweb also provided such probabilty.

Plugin System
---------------

Uliweb provides a simple plugin system. When running at some important points, 
Uliweb will invoke special function to invoke plugin functions. So plugin 
system of Uliweb consists with three components: invoking point, plugin collection
system, plugin process functions. 

**Invoking point** will invoke all matched 
plugin functions, and each invoking point may have several pluging functions at a time.
And these functions could have priority attribute, so before executing these 
functions, they will be sorted according the priority value. There are two kinds
of invoking way, one it ``call``, this way will invoking plugin functions one by one,
you can't stop it at the middle of execution, and it'll return nothing;
and the other is ``exec``, this way will invoking plugin functions also one by one,
but if any function return a value is not ``None``, the execution will stop and the
value will be returned. So you can choice the suitable way fits your needs.

A invoking point is not only used for invoking plugin functions, it's also defined
the arguments used in this invoking point, for example, here is a invoking point:

.. code:: python

    callplugin(self, 'startup_installed')
    
All invoking points are just functions, the first arugment of it must be the sender
object, and you can also use other arguments. And there is a special argument
``signal``, is can be just simple type, for example, ``None``, or a string. If the 
invoking point set this argument, plugin function can match it or just skip it,
it depends on how do you define your plugin function, will see it below.

There are four kind of function:

* callplugin Can't be interrupted and will return nothing, can be executed many times
* callplugin_once Just like above, but can only be executed once
* execplugin Can be interrupted and will return a value(if any plugin function
  return a value is not ``None``, the execution will be interrupted)
* execplugin_once Just like above, but can only be executed once, and invoke
  it the next time, it'll return the first return value.

**Plugin collection system** will be used for collection all plugin functions. 
and when Uliweb executing the invoking point, it'll find the matched plugin
functions from the collection system. But you should define plugin function 
first. Which places are the mose suitable place to writing the plugin functions?
The answer is in each settings.py, because they'll be imported automatically
when the Uliweb started.
