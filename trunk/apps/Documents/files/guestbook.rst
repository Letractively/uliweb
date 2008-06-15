�������԰�
=============

:Author: Limodou <limodou@gmail.com>

.. contents:: 
.. sectnum::

Ҳ�����Ѿ�ѧ���� `Hello, Uliweb <hello_uliweb>`_ ��ƪ�̳̣���Uliweb�Ѿ�����һ�����Ե�
��ʶ����ô�ã����������ǽ������ݿ�����磬��һ�����ʹ�ü򵥵����ݿ⡣

׼��
------

��Uliweb��Դ�����Ѿ���һ�����԰�Ĵ��롣���غ����÷�������

::

    manage.py runserver
    
Ȼ������������� http://localhost:8000/guestbook �����Ϳ��Կ����ˡ�Ŀǰȱʡ��ʹ��
sqlite3������㰲װ��python 2.5���Ѿ������õġ�����Ҫ��װ��Ӧ�����ݿ��Python�İ�ģ
�顣ĿǰUliwebʹ��geniusql��Ϊ���ݿ�ײ���������֧�ֶ������ݿ⣬�磺mysql, sqlite,
postgresql, sqlserver, access,��firebird��������ֻ�Թ�mysql��sqlite��

���ˣ�Դ��׼�����ˣ���һ����׼������������

��������
-----------

��ΪUliweb���Ѿ�������GuestBook�Ĵ��룬��������ܲ�ϣ����UliwebĿ¼�½��й�������ôUliweb
�������㽫������Ŀ�ɾ��ص�����һ��Ŀ¼�¡�ִ��:

::

    manage.py export Ŀ¼
    
����������Uliweb�Ļ�������ȫ����һ���µĻ������ˡ�Ȼ���������µ�Ŀ¼����ʼ�����ɡ�

����APP
-----------

����ǰ�洴����Ŀ¼����ʱapps���ܻ������ڣ���ôUliweb�ṩ��makeapp������Դ���һ���յ�app�ṹ��
ִ��:

::

    manage.py makeapp GuestBook
    
�������Զ��ᴴ��apps����ص�GuestBookĿ¼��

�������ݿ�
------------

Uliweb�е����ݿⲻ��ȱʡ��Ч�ģ��������Ҫ����һ�²ſ���ʹ�á�����Uliweb��Ȼ�ṩ�����ѵ�
ORM����������Բ�ʹ������Uliweb�ṩ�˲�����ƣ������������׵����ʵ���ʱ��ִ�г�ʼ���Ĺ�����
��GuestBook/settings.py�ļ�����������Կ����Ѿ����ڣ�

.. code:: python

    from utils.plugin import plugin
    
plugin��һ��decorator����exposeһ������������������κ����������Ϳ������ҽӺ�����һ��
ִ�е�����ϣ����ҵ�����ִ�е������ʱ�����Զ�ִ�����ҽӵĺ������ã������������ݣ�

.. code:: python

    connection = {'connection':'sqlite://database.db'}
    #connection = {'connection':'mysql://root:limodou@localhost/test'}
    
    DEBUG_LOG = True
    
    @plugin('prepare_template_env')
    def prepare_template_env(env):
        from utils.textconvert import text2html
        env['text2html'] = text2html
        
    @plugin('startup')
    def startup(application, config, *args):
        from utils import orm
        orm.set_debug_log(DEBUG_LOG)
        orm.set_auto_bind(True)
        orm.set_auto_migirate(True)
        orm.get_connection(**connection)
        
����һ��������͡�

���ݿ����Ӳ���
~~~~~~~~~~~~~~

connection �����������ݿ��������ã�����һ���ֵ䡣����connection�Ǳ���ģ���Ӧһ�����ݿ�
�����ַ����������������������д�����Ӵ��Ĳ��������Խ�������connection����ֵ��С�

��������ʹ����sqlite���ݿ⣬�����mysql�������ǰ���������ôע�͵ĸ�ʽ��д��

�����ַ����Ļ�����ʽΪ��

::

    provider://username:password@localhost:port/dbname?argu1=value1&argu2=value2
    
������Щ�����ǿ���ȱʡ����֯��Ϊ�ֵ������connection�еġ����磺

::

    connection = {'connection':'mysql://localhost/test',
        'username':'limodou',
        'password':'password'}
    connection = {'connection':'mysql://localhost/test?username=limodou&password=password'}
    connection = {'connection':'mysql://limodou:password@localhost/test'}
    
��������д��Ч����һ���ġ������Щ����û���ṩ����port��������ʹ��ȱʡֵ������sqlite��
��Ϊû��ʲô�û����Ϳ���֮��ģ����Կ���ֱ��дΪ��

::
    
    connection = {'connection':'sqlite'}    #�������ݿ�
    connection = {'connection':'sqlite://'} #�ڴ����ݿ�
    connection = {'connection':'sqlite'://path'}    #ʹ���ļ�
    
ǰ������һ���ģ���һ�ֽ�ʹ���ļ���Ϊ���ݿ⡣��ô�����Ǿ���·��Ҳ���������·����
    
���ݿ��ʼ��
~~~~~~~~~~~~

�������趨һ������ ``DEBUG_LOG = True`` ��ע��ȫ���Ǵ�д���������������Ƿ�Ҫ���������Ϣ����
��Ϊ�ײ��SQL��䡣

Ȼ��

.. code:: python

    @plugin('startup')
    def startup(application, config, *args):
        from utils import orm
        orm.set_debug_log(DEBUG_LOG)
        orm.set_auto_bind(True)
        orm.set_auto_migirate(True)
        orm.get_connection(**connection)

������Uliweb��ִ�е�startup��λ��ʱ�������صĲ��������startup�ǲ���������õ�����֣�
�Ѿ���SimpleFrame.py�ж����ˡ�ÿ�����õ㶼�����ѵ����ֺͽ�Ҫ���ݵĲ�����startup������
application��config����������*args��Ϊ���Ժ���չʹ�á�

����������ݿ��ʼ���Ĺ����ˡ���ΪUliweb������һ�����ݿ⣬��˳�ʼ���Ĺ�����Ҫ����������
�����ͱȽ����ɡ�ͬʱ��ΪUliweb��֯��ʽΪAPPģʽ����������ʱ���Զ���������APP�µ�settings.py
�����е��룬�������ò������ռ������������Ϳ�����ÿ��APP�µ�settings.pyд������Ҫ����
�ô���һ����һ���ط��趨�ģ����൱��ȫ����Ч�ˡ��������ַ�ʽ��ʹ�ã�����ϣ��ÿ��APP����
�ܶ���ʱ�ǳ����á������Uliweb�е�APP��һ���������Ա��������ѵĽṹ������������̬�ļ���
�����ļ�����ͬʱ����ҪʱҲ����ֱ�ӷ�������APP����Ϣ��

``set_debug_log(DEBUG_LOG)`` ����������ʾ�ײ��SQL���ڿ��������������£�������ʾ���������ϡ�

``set_auto_bind(True)`` �Զ������á��������㵼��һ��Modelʱ�������Զ���ȱʡ�����ݿ�����
���а󶨣��Ϳ���ֱ��ʹ���ˡ���Ȼ������Ҫ�ֶ���ÿ��Model��Ҫ���ĸ����ӹ�������ֻ�е�����
����ʱ���Դ򿪣���ʹ�ö���������ʱ���Թرգ�Ȼ������ֹ��󶨴���

``set_auto_migirate(True)`` ������úܴ����ȣ����������ʱ�������ڣ���Uliweb�����Զ���
����ṹ����Σ������ʹ�ù�web2py�����֪����Model�����仯ʱ�����Զ����±�ṹ����ô
UliormҲ��������������Ŀǰ�Ƚϼ򵥣�ֻ�ܴ��������ӣ�ɾ�����޸�
������������޸ģ����ܻ�������ݶ�ʧ�������޷��ж��ֶεĸ���������һ����������ʵ����ɾ����
�ģ������µģ��������ݻᶪʧ��������԰�������عرգ��ֹ��޸����ݿ⣬ͬʱ�������ݵı��ݡ�
����Ϊ�������ݱ��ݣ�Ȼ��ͨ���ָ��������ָ����ȫ�ġ���������Uliweb��û������Ĺ��ߡ�

�����Զ�Ǩ���ڿ���ʱ�û����ؿ����޸ı�ṹ�Ĺ�����ֻҪ���˾���Ч����ǳ����㡣

�������������趨���Ϳ�����Uliweb�����·ǳ������ʹ�����ݿ��ˡ�ֻҪ����ã�ʹ���������ˡ�
�󽨱��޸ı�ṹȫ���Զ���ɣ��ǳ����㡣

``orm.get_connection(**connection)`` ���������ݿ����Ӷ��󣬲�����������ص��趨���б�Ҫ��
��ʼ������������������趨��Ҫ�ڵ���get_conection()ǰ��ɡ��ڵ�����get_connection()֮
�󣬴��������ӽ���Ϊȱʡ���ӹ�ȫ��ʹ�á�

ģ�廷������չ
----------------

��settings.py�л���һ��������

.. code:: python

    @plugin('prepare_template_env')
    def prepare_template_env(env):
        from utils.textconvert import text2html
        env['text2html'] = text2html

��Ҳ��һ�������ʹ��ʾ����������ģ��Ļ�����ע��һ���µĺ��� ``text2html``, ������Ϳ���
��ģ����ֱ��ʹ��text2html��������ˡ�������Ϊ����������ȫ����Ч�ģ�����������APP����
��������

``text2html`` �����þ��ǽ��ı�תΪHTML��ʽ������Link�Ĵ�����������ǰ�ڿ���Djangoʱд�ġ�

׼��Model
-----------

��GuestBookĿ¼�´���һ����Ϊmodels.py���ļ�������Ϊ��

.. code:: python

    from utils.orm import *
    import datetime
    
    class Note(Model):
        username = Field(str)
        message = Field(str, max_length=1024)
        homepage = Field(str)
        email = Field(str)
        datetime = Field(datetime.datetime)
        
�ܼ򵥡�

����Ҫ�� utils.orm �е���ȫ�������������򵥡�

Ȼ���ǵ���datetimeģ�顣Ϊʲô���õ�������ΪUliorm�ڶ���Modelʱ֧�����ֶ��巽ʽ��

* ʹ���ڲ���Python���ͣ��磺int, float, unicode, datetime.datetime, datetime.date,
  datetime.time, decimal.Decimal, str, bool�����⻹��չ��һЩ���ͣ��磺blob, text��
  �������ڶ���ʱֻҪʹ��Python�����;ͺ��ˡ�
* Ȼ�������GAEһ����ʹ�ø���Property�࣬�磺StringProperty, UnicodeProperty,
  IntegerProperty, BlobProperty, BooleanProperty, DateProperty, DateTimeProperty,
  TimeProperty, DecimalProperty, FloatProperty, TextProperty��

һ��Model��Ҫ�� ``Model`` ��������Ȼ��ÿ���ֶξ��Ƕ���Ϊ�����ԡ�Field()��һ������������
����ݵ�һ�����������Ҷ�Ӧ�������࣬��ˣ�

.. code:: python

    class Note(Model):
        username = StringProperty()
        message = TextProperty(max_length=1024)
        homepage = StringProperty()
        email = StringProperty()
        datetime = DateTimeProperty()
        
ÿ���ֶλ�������һЩ���ԣ��糣�õģ�

* default ȱʡֵ
* max_length ���ֵ
* verbose_name ��ʾ��Ϣ

�ȡ�����Ļ�ͷ�һ���ϸ�������ĵ��н���˵����

.. note::

    �ڶ���Modelʱ��Uliorm���Զ�Ϊ�����id�ֶεĶ��壬������һ����������һ����Djangoһ����
    
��ʾ����
-----------------------

����guestbook()��View����
~~~~~~~~~~~~~~~~~~~~~~~~~~

��GuestBook�µ�views.py�ļ����Ѿ��������ˣ�

.. code:: python

    #coding=utf-8
    from frameworks.SimpleFrame import expose

������ʾ���ԵĴ���

.. code:: python

    @expose('/guestbook')
    def guestbook():
        from models import Note
        
        notes = Note.filter(order=lambda z: [reversed(z.datetime)])
        return locals()

�ȶ���urlΪ ``/guestbook`` ��

Ȼ����guestbook()�����Ķ��塣�����ȵ���Note�࣬Ȼ��ͨ�������෽��filter�������ݿ�Ĳ�
ѯ��Ϊ�˰�ʱ�䵹����ʾ������filter�ж�order������һ��lambda������������geniusql���﷨��
�Ժ�Ҳ���ܻ�֧���������﷨�� ``lambda z: [reversed(z.datetime)]`` �����������˼����
�� ``z`` ������ ``datetime`` �ֶν��е��������Կ�������Python���﷨��reversed��һ��
Python�����ú�����

������һЩ�򵥵��÷���

.. code:: python

    notes = Note.filter()               #ȫ����¼����������
    note = Note.get(3)                  #��ȡidֵΪ3�ļ�¼
    note = Note.get(username='limodou') #��ȡusernameΪlimodou�ļ�¼
    
Ȼ�����Ƿ���locals()����ģ����ʹ������

.. note::

    ��Uliweb��ÿ�����ʵ�URL��View֮��Ҫͨ��������ʵ�֣���ʹ��expose������Ҫһ��URL��
    ������Ȼ��������ʱ��������URL�������ε�View�������ж�Ӧ��View������ת��Ϊ��
    
        appname.viewmodule.functioname
        
    ����ʽ��������һ���ַ�����Ȼ��ͬʱUliweb���ṩ��һ��������url_for��������������
    View�������ַ�����ʽ�Ͷ�Ӧ�Ĳ�������������URL�����������������ӣ��ں����ģ������
    �ǽ�������

����guestbook.htmlģ��
~~~~~~~~~~~~~~~~~~~~~~~~

��GuestBook/templatesĿ¼�´�����View����ͬ����ģ�壬��׺Ϊ.html����guestbook.html��
����������ݣ�

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
    
��һ�н���base.htmlģ����м̳С����ﲻ���˵��ֻ��Ҫע����base.html����һ��{{include}}
�Ķ��壬����ʾ��ģ��Ҫ�����λ�á�����Դ�Uliweb��Դ���н�base.html���������Ŀ¼�¡�

h2 ��ʾһ����׼��������һ�����ӣ������ӵ�������Ե�URL��ȥ�ˡ�ע��ģ��û�н���ʾ����ӵ�
Formд��һ����Ϊ��������Ƚ϶࣬ͬ������û�����������ٴ���ʾ���е�����(��Ϊ����
û�п��Ƿ�ҳ)����������Ƚ��������Էֳɲ�ͬ�Ĵ����ˡ�

``{{for}}`` ��һ��ѭ������סUliwebʹ�õ���web2py��ģ�壬���������˸��졣������{{}}�еĴ���
�����������Python���룬����Ҫע�����Python���﷨����˺����':'�ǲ���ʡ�ġ�Uliweb��ģ
�������㽫���붼д��{{}}�У�������HTML������Ϊ����Python���룬Ҫʹ�� ``out.write(htmlcode)`` 
���ִ����������Ҳ���Խ�Python����д��{{}}�У���HTML��������������棬�������������ġ�

��ѭ���ж�notes�������д���Ȼ����ʾһ��ɾ����ͼ�����ӣ��û���Ϣ���û����ԡ�

���� ``{{=text2html(n.message)}}`` ������ʹ����������settings.py�ж����text2html��
�����ı����и�ʽ������

``{{pass}}`` �Ǳ���ġ���Uliwebģ���У�����Ҫ����������������Ҫ�ڿ�������ʱ���pass����ʾ��
������������൱�ڰ�Python���������ϸ�Ҫ�������ת�����ǳ����㡣

�ã��ھ�������Ĺ�������ʾ���ԵĹ���������ˡ�����Ŀǰ������������ԣ���һ���������ǿ���
��������ԡ�

.. note::

    ��Ϊ��base.html�к�guestbook.html�õ���һЩcss��ͼ���ļ����������Դ�Uliweb��
    GuestBook/staticĿ¼�½�ȫ���ļ����������Ŀ¼�¡�
    
��������
----------

����new_comment()��View����
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

��ǰ���ģ�������Ƕ������������Ե����ӣ�

.. code:: html

    <a href="{{=url_for('%s.views.new_comment' % request.appname)}}">New Comment</a>
    
���Կ���������ʹ����url_for�����ɷ�������ӡ�����url_for��ǰ���Ѿ����ˣ�����Ҫע��ľ���
������Ϊnew_comment�����������Ҫ��views.py������������һ��������

��views.py���������´��룺

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

���Կ��������� ``/guestbook/new_comment`` ��

�������ǵ�����һЩģ�壬����Note���Model����ôNoteForm��ʲô�أ�������������¼��Form��
���󣬲��ҿ������������ݽ���У�顣һ�����������н��ܡ�

Ȼ�󴴽�form����

�ٸ���request.method��GET����POST��ִ�в�ͬ�Ĳ���������GET����ʾһ����Form������POST
��ʾ�û��ύ�����ݣ�Ҫ���д���ʹ��GET��POST������ͬһ�������´���ͬ�Ķ���������һ��
Լ����һ���ж�����ʹ��GET��д���޸Ĳ���ʹ��POST��

��request.methodΪGETʱ������ֻ�Ƿ��ؿյ�form�����һ���յ�message������form.html()��
�Է���һ���յ�HTML�����롣��message��������ʾ�������Ϣ��

��request.methodΪPOSTʱ�� ���ȵ��� ``form.validate(request.params)`` �����ݽ���У�顣
��������һ����Ԫ��tuple����һ��������ʾ�ɹ����ǳ����ڶ���Ϊ�ɹ�ʱ��ת��ΪPython��ʽ��
�����ݣ�ʧ��ʱΪ������Ϣ��

��flagΪTrueʱ�����гɹ�����һ�����ǿ��Կ����ڱ��в�û��datetime�ֶΣ������������
�ֹ����һ��ֵ����ʾ�����ύ��ʱ�䡣Ȼ��ͨ�� ``n = Note(**data)``` ������Note��¼�������ﲢû����
�������ݿ��У������ִ��һ�� ``n.put()`` �������¼�����ݿ��С�ʹ�� ``n.save()`` Ҳ���ԡ�

Ȼ��ִ����Ϻ󣬵��� ``redirect`` ����ҳ�����ת���������԰����ҳ��������ʹ����url_for����
���������ӡ�ע��redirectǰ����Ҫ�� ``return`` ��
    
��flagΪFalseʱ�����г���������������message�������˳�����ʾ��Ȼ��ͨ��
``form.html(request.params, data, py=False)`` �����ɴ�������Ϣ�ı�������dataΪ����
��Ϣ�� ``py=False`` �Ǳ�ʾ��ʹ������ʱ������Python����ת������ΪForm��У������֮������
����������������ͣ����ϴ�������ת��ΪPython���ڲ����ݣ��磺int, float֮��ġ����ǵ�����
ʱ��������ת�����Python���ݣ���˲���������ת������ʱҪʹ�� ``py=False`` ���������data
��У��ɹ������ݣ�����ͨ������ʾ����������ֱ��ʹ�� ``form.html(data)`` �Ϳ����ˡ�

����¼���
~~~~~~~~~~~~~

Ϊ�����̨���н��������û�����ͨ���������������¼�룬��Ҫʹ��HTML��formϵ��Ԫ��������
¼��Ԫ�ء������о����Web�����߿���ֱ����дHTML���룬���Ƕ��ڳ�ѧ�ߺ��鷳�������㻹Ҫ����
���������ݸ�ʽת���Ĵ����������ܶ��ṩ�����ɱ��Ĺ��ߣ�UliwebҲ�����⡣Formģ
����Ǹ�����õġ�

��GuestBookĿ¼�´���forms.py�ļ���Ȼ��������´��룺

.. code:: python

    from utils import Form
    
    Form.Form.layout_class = Form.CSSLayout
    
    class NoteForm(Form.Form):
        message = Form.TextAreaField(label='Message:', required=True)
        username = Form.TextField(label='Username:', required=True)
        homepage = Form.TextField(label='Homepage:')
        email = Form.TextField(label='Email:')

���ȵ���Formģ�飬Ȼ���趨Form��ʹ��css���֡�ĿǰUliweb��Form�ṩ���ֲ��֣�һ����ʹ��
tableԪ�����ɵģ���һ����ʹ��divԪ�����ɵġ�table������ȱʡ�ġ�

���ž��Ǵ���NoteFormԪ���ˡ������Ҷ�����4���ֶΣ�ÿ���ֶζ�Ӧһ�����͡���TextAreaField
��ʾ���е��ı��༭��TextField��ʾ�����ı����㻹����ʹ����HiddenField, SelectField,
FieldField, IntField, PasswordField, RadioSelectField���ֶ����͡�ĿǰForm�Ķ��巽ʽ
��Uliorm�Ĳ�̫һ�£���ΪForm������ʱ����磬�Ժ�Ҳ���Կ���дһ��ͳһ��Field������һ����
�Ĵ���

Ҳ���㿴���ˣ���������һЩ�Ǵ������͵ģ���IntField����ô������ת��Ϊ��Ӧ��Python������
�ͣ�ͬʱ������HTML����ʱ��ת�����ַ�����

ÿ��Field���Ϳ��Զ������ɵĲ������磺

* label ������ʾһ����ǩ
* required ����У���Ƿ����룬��������Ϊ��
* default ȱʡֵ
* validators У����

����Model�Ķ��壬��������ͬ��

��дnew_comment.htmlģ���ļ�
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

��GuestBook/templates�´���new_comment.html��Ȼ������������ݣ�

.. code:: html

    {{extend "base.html"}}
    {{if message:}}
    <p class="message">{{=message}}</p>
    {{pass}}
    <h1>New Comment</h1>
    <div class="form">
    {{Xml(form)}}
    </div>

������ ``{{extend "base.html"}}`` ��ʾ��base.html�̳С�

Ȼ����һ�� if �ж��Ƿ���message��Ϣ�����������ʾ������Ҫע��if�����':'�š�

Ȼ����ʾformԪ�أ�����ʹ���� ``{{Xml(form)}}`` ��form�Ǵ�View�д���ģ���Xml()��ģ����
�����÷�����������ԭ��������ݣ���HTML�ı�ǩ�������ת������ {{=variable}} ����variable
������HTML��ǩ����ת������ˣ�����������ԭʼ��HTML�ı���Ҫʹ��Xml()�������

���ڿ��������������һ���ˡ�

ɾ������
----------

��ǰ��guestbook.html�У�������ÿ������ǰ������һ��ɾ����ͼ�����ӣ���ʽΪ��

.. code::

    <a href="/guestbook/delete/{{=n.id}}"><img src="/static/delete.gif"/></a>
    
��ô�����������ʵ������

��GuestBook/views.py�ļ���Ȼ����ӣ�

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

ɾ���ܼ򵥣�����Note��Ȼ��ͨ�� ``Note.get(int(id))`` ���õ�����Ȼ���ٵ��ö����delete()
������ɾ����

URL��������
~~~~~~~~~~~~

��ע�⣬����exposeʹ����һ���������� ``<id>`` ��ʽ��һ����expose�е�url����
����<type:para>����ʽ���ͱ�ʾ������һ������������type:����ʡ�ԣ���������int�����͡���
int���Զ�ת��Ϊ ``\d+`` ������ʽ������ʽ��Uliweb��������: int, float, path, any, string,
regex�����͡����ֻ�� ``<name>`` ���ʾƥ�� //��������ݡ�һ����URL�ж����˲���������Ҫ
��View������Ҳ��Ҫ������Ӧ�Ĳ��������del_comment������дΪ�ˣ� ``del_comment(id)`` ��
�����id��URL�е�id��һ���ġ�

���ˣ������������һ��ɾ�������Ƿ�����ˡ�

����ҳ��
~~~~~~~~~~~~~~~~

���������ʱ���������Ҫ���û���ʾһ��������Ϣ����˿���ʹ��error()����������һ������
��ҳ�档����ǰ�治��Ҫreturn��ֻ��Ҫһ��������Ϣ�Ϳ����ˡ�

��ô������Ϣ��ģ����ô�����أ������templatesĿ¼�¶���һ����Ϊerror.html���ļ�������
��һЩ���ݼ��ɡ�

����error.html��Ȼ���������´��룺

.. code:: html

    {{title="Error"}}
    {{extend "base.html"}}
    <h1>Error!</h1>
    <p>{{=message}}</p>


���ҳ��ܼ򵥣����Ƕ�����һ��title������Ȼ���Ǽ̳�base.html���ٽ�������ʾ�������ݡ�

����������һ������Ҫ�ļ��ɣ��Ǿ����� {{extend}} ǰ�涨�����������Ⱦģ��ʱ������������
ǰ�档������һ����ģ������һЩ������Ҫ����������û��ͨ��View���������룬��������ģ��
������������ͨ�����ַ����Ϳ��Խ��������ʹ������ǰ�棬�Ӷ����ᱨδ����Ĵ���

.. note::

    �����Ҷ�web2pyģ���һ����չ����ǰweb2pyҪ��{{extend}}�ǵ�һ�еģ������ڿ��Բ��ǡ�
    �������ִ�����ԺܺõĴ�������ģ���ж����ڸ�ģ����Ҫʹ�õı����������
    
����
-------

����ѧϰ�������˽���������ݣ�

#. ORM��ʹ�ã�������ORM�ĳ�ʼ�����ã�Model�Ķ��壬�򵥵����ӣ�ɾ������ѯ
#. Formʹ�ã�������Form�Ķ��壬Form�Ĳ��֣�HTML�������ɣ�����У�飬������
#. ģ���ʹ�ã������� {{extend}} ��ʹ�ã���ģ�廷���������Զ��庯������ģ����������
   ���ɣ�����ģ���ʹ�ã�Python�����Ƕ��
#. View��ʹ�ã�������redirect, error��ʹ��
#. URLӳ���ʹ�ã�������expose��ʹ�ã��������壬��View�����Ķ�Ӧ
#. manage.py��ʹ�ã�������export, makeapp��ʹ��
#. �ṹ���˽⣬������Uliweb��app��֯��settings.py�ļ��Ĵ�����ƣ�view������ģ���ļ�
   �Ķ�Ӧ��ϵ

���ݺܶ࣬��ȷ������Щ��ԶԶ����һ����ܵ�ȫ��������Ӧ�õĸ��ӣ���ܵĹ���Ҳ��Խ��Խ�ࡣ
��һ���õĿ��Ӧ�þ������о�������������ȹ�����һ��������ʹ�ã����ڹ���Ļ�����Ȼ��
���Ŷ��е��������������ȥ�������öԿ���о�����˶Ի������в��ϵĵ��������ƣ�ʹ��Խ��
Խ�����ǿ��Uliweb�����������Ŀ��ǰ����