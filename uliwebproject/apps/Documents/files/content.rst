`Simplified Chinese Version <{{= url_for('%s.views.documents' % request.appname)+'?lang=zh' }}>`_

Basic Info
---------------------
{{ 
def index(filename):
    return url_for('%s.views.show_document' % request.appname, filename=filename)
pass
}}
* `Introduction <{{= index('introduction') }}>`_
* `License <{{= index('license') }}>`_
* `Credits <{{= index('credits') }}>`_
* `Community & Links <{{= index('community') }}>`_
* `Web sites that use Uliweb <{{= index('sites') }}>`_

Installation
-------------------------

* `Install Uliweb <{{= index('installation') }}>`_

Tutorials
-------------------------------

* `Hello, Uliweb(Easy) <{{= index('hello_uliweb') }}>`_
* `Mini GuestBook(Hard) <{{= index('guestbook') }}>`_

References
-----------------------------

* `Architecture and Mechanism <{{= index('architecture') }}>`_
* `URL Mapping <{{= index('url_mapping') }}>`_
* `Views <{{= index('views') }}>`_
* `Templates <{{= index('template') }}>`_
* `Database and ORM <{{= index('orm') }}>`_
* `Deployment Guide <{{= index('deployment') }}>`_
* `uliweb Command Guide <{{= index('manage_guide') }}>`_
* `I18n <{{= index('i18n') }}>`_
* `Form <{{= index('form') }}>`_
* `Global Environment <{{= index('globals') }}>`_

Advanced Topics
-----------------------------

* `Extending Uliweb <{{= index('extending') }}>`_
* `settings.ini Details(not finished) <{{= index('settings') }}>`_

Apps List
-------------

* `uliweb.contrib.staticfiles(not finished) <{{= index('app_staticfiles') }}>`_
* `uliweb.contrib.orm(not finished) <{{= index('app_orm') }}>`_
* `uliweb.contrib.template(not finished) <{{= index('app_template') }}>`_
