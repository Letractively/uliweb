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
* Change Log
* `Credits <{{= index('credits') }}>`_
* `Community & Links <{{= index('community') }}>`_
* `Web sites which use Uliweb <{{= index('sites') }}>`_

Installation
-------------------------

* `Install Uliweb <{{= index('installation') }}>`_
* `How to update Uliweb to new version <{{= index('update') }}>`_
* How to config Uliweb

Tutorials
-------------------------------

* `Hello, Uliweb(Easy) <{{= index('hello_uliweb') }}>`_
* `Mini GuestBook(Hard) <{{= index('guestbook') }}>`_
* Views and Templates
* Build a weblog in minutes
* CSS Artwork for your weblog
* Go ahead with Uliweb
* Reference list

References
-----------------------------

* `Architecture and Mechanism <{{= index('architecture') }}>`_
* `URL Mapping <{{= index('url_mapping') }}>`_
* `Views <{{= index('views') }}>`_
* Templates
* Database and ORM
* `Deployment Guide <{{= index('deployment') }}>`_
* `manage.py User Guide <{{= index('manage_guide') }}>`_
* `I18n <{{= index('i18n') }}>`_

Advanced Topics
-----------------------------

* `Extending Uliweb <{{= index('extending') }}>`_
* Full Details of Configuration Files
* Security
* Error Handling
* Ajax in Uliweb

Class Reference
------------------------------

Additional Topics
-------------------------------

* Quick Reference Chart


