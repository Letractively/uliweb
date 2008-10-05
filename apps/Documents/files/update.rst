How to update Uliweb to new version
======================================

:Author: Limodou <limodou@gmail.com>

In the commonly situation, you'll not work at the Uliweb's source code directory
directly, because it includes all source code of uliwebproject site. So before
you really starting to work, you should do the first thing is prepare a clear
working directory, you can do it by running manage.py command tool, for example: 

::

    python manage.py export [-e] outputdir
    
    -e
        Completely sync operation. It'll delete the old version of Uliweb in 
        outputdir directory first, then do the copy work.
    
So you can use ``export`` command to create a clear working directory.

While the Uliweb is updated to a new version, you can still use ``export`` to
copy the newest source files to ``outputdir`` directory.

