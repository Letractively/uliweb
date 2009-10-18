#coding=utf-8
import time, sys
sys.path.insert(0, '../uliweb/lib')
from uliweb.orm import *

#basic testing
def test_1():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(unicode)
    ...     year = Field(int, default=0)
    >>> a = Test(username='limodou').save()
    >>> print a
    <Test {'username':u'limodou','year':0,'id':1}>
    >>> b = Test(username=u'limodou1').save()
    >>> print b
    <Test {'username':u'limodou1','year':0,'id':2}>
    >>> print list(Test.all())
    [<Test {'username':u'limodou','year':0,'id':1}>, <Test {'username':u'limodou1','year':0,'id':2}>]
    >>> print Test.count()
    2
    >>> a.username
    u'limodou'
    >>> list(Test.filter(Test.c.username==u'limodou'))
    [<Test {'username':u'limodou','year':0,'id':1}>]
    >>> c = Test.get(1)
    >>> c
    <Test {'username':u'limodou','year':0,'id':1}>
    >>> c = Test.get(Test.c.id==1)
    >>> c
    <Test {'username':u'limodou','year':0,'id':1}>
    >>> Test.remove(1)
    >>> Test.count()
    1
    >>> Test.remove([3,4,5])
    >>> Test.count()
    1
    >>> Test.remove(Test.c.id==2)
    >>> Test.count()
    0
    """
    
#testing model alter one the fly
def test_2():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    ...     name = Field(str, max_length=65536)
    >>> class Test(Model):
    ...     username = Field(str, max_length=20)
    ...     year = Field(int)
    >>> Test.table.columns.keys()
    ['username', 'id', 'year']
    """
    
#testing many2one
def test_3():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    >>> class Test1(Model):
    ...     test1 = Reference(Test, collection_name='test1')
    ...     test2 = Reference(Test, collection_name='test2')
    ...     name = Field(str)
    >>> a1 = Test(username='limodou1').save()
    >>> a2 = Test(username='limodou2').save()
    >>> a3 = Test(username='limodou3').save()
    >>> b1 = Test1(name='user', test1=a1, test2=a1).save()
    >>> b2 = Test1(name='aaaa', test1=a1, test2=a2).save()
    >>> b3 = Test1(name='bbbb', test1=a2, test2=a3).save()
    >>> a1
    <Test {'username':u'limodou1','year':0,'id':1}>
    >>> list(a1.test1.all())[0]
    <Test1 {'test1':<Test {'username':u'limodou1','year':0,'id':1}>,'test2':<Test {'username':u'limodou1','year':0,'id':1}>,'name':u'user','id':1}>
    >>> a1.test1.count()
    2
    >>> list(a2.test2.all())
    [<Test1 {'test1':<Test {'username':u'limodou1','year':0,'id':1}>,'test2':<Test {'username':u'limodou2','year':0,'id':2}>,'name':u'aaaa','id':2}>]
    >>> b1.test1
    <Test {'username':u'limodou1','year':0,'id':1}>
    >>> a1.username = 'user'
    >>> Test.get(1)
    <Test {'username':u'limodou1','year':0,'id':1}>
    >>> x = a1.save()
    >>> Test.get(1)
    <Test {'username':u'user','year':0,'id':1}>
    """
    
#testing many2one using collection_name
def test_4():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    >>> class Test1(Model):
    ...     test = Reference(Test, collection_name='tttt')
    ...     name = Field(str)
    >>> a1 = Test(username='limodou1').save()
    >>> b1 = Test1(name='user', test=a1).save()
    >>> b2 = Test1(name='aaaa', test=a1).save()
    >>> a1
    <Test {'username':u'limodou1','year':0,'id':1}>
    >>> list(a1.tttt.all())[0]   #here we use tttt but not test1_set
    <Test1 {'test':<Test {'username':u'limodou1','year':0,'id':1}>,'name':u'user','id':1}>
    >>> a1.tttt.count()
    2
    >>> b3 = Test1(name='aaaa').save()
    >>> a1.tttt.count()
    2
    >>> b3.test = a1
    >>> b3.save()
    <Test1 {'test':<Test {'username':u'limodou1','year':0,'id':1}>,'name':u'aaaa','id':3}>
    >>> Test1.get(3)
    <Test1 {'test':<Test {'username':u'limodou1','year':0,'id':1}>,'name':u'aaaa','id':3}>
    """
    
#testing transaction
def test_5():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(unicode)
    ...     year = Field(int, default=0)
    >>> t = db.begin()
    >>> a = Test(username='limodou').save()
    >>> b = Test(username='limodou').save()
    >>> db.rollback()
    >>> Test.count()
    0
    >>> t = db.begin()
    >>> a = Test(username='limodou').save()
    >>> b = Test(username='limodou').save()
    >>> db.commit()
    >>> Test.count()
    2
    """
  
#testing OneToOne
def test_6():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    >>> class Test1(Model):
    ...     test = OneToOne(Test)
    ...     name = Field(str)
    >>> a1 = Test(username='limodou1').save()
    >>> b1 = Test1(name='user', test=a1).save()
    >>> a1
    <Test {'username':u'limodou1','year':0,'id':1}>
    >>> a1.test1
    <Test1 {'test':<Test {'username':u'limodou1','year':0,'id':1}>,'name':u'user','id':1}>
    >>> b1.test
    <Test {'username':u'limodou1','year':0,'id':1}>
    """
    
#test ManyToMany
def test_7():
    """
    >>> set_debug_query(True)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class User(Model):
    ...     username = Field(unicode)
    >>> class Group(Model):
    ...     name = Field(str)
    ...     users = ManyToMany(User)
    >>> a = User(username='limodou').save()
    >>> b = User(username='user').save()
    >>> c = User(username='abc').save()
    >>> g1 = Group(name='python').save()
    >>> g2 = Group(name='perl').save()
    >>> g3 = Group(name='java').save()
    >>> g1.users.add(a)
    >>> g1.users.add(b, 3) #add can support multiple object, and object can also int
    >>> try:
    ...     g1.users.add(a, b)  #can't has duplicated records
    ... except Exception, e:
    ...     print e
    (IntegrityError) columns group_id, user_id are not unique u'INSERT INTO group_user_users (group_id, user_id) VALUES (?, ?)' [1, 1]
    >>> list(g1.users.all())
    [<User {'username':u'limodou','id':1}>, <User {'username':u'user','id':2}>, <User {'username':u'abc','id':3}>]
    >>> g1.users.delete(a)
    >>> g1.users.clear()
    >>> g1.users.count()
    0
    >>> g1.users.add(a, b, c)
    >>> g2.users.add(a)
    >>> list(a.group_set.all())
    [<Group {'name':u'python','id':1}>, <Group {'name':u'perl','id':2}>]
    >>> a.group_set.add(g3)
    >>> list(a.group_set.all())
    [<Group {'name':u'python','id':1}>, <Group {'name':u'perl','id':2}>, <Group {'name':u'java','id':3}>]
    >>> g1.users.delete(a)
    >>> list(g1.users.all())
    [<User {'username':u'user','id':2}>, <User {'username':u'abc','id':3}>]
    >>> list(g2.users.all())
    [<User {'username':u'limodou','id':1}>]
    >>> list(a.group_set.all())
    [<Group {'name':u'perl','id':2}>, <Group {'name':u'java','id':3}>]
    """

#test SelfReference
def test_8():
    """
    >>> set_debug_query(True)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class User(Model):
    ...     username = Field(unicode)
    ...     parent = SelfReference(collection_name='children')
    >>> a = User(username='a').save()
    >>> b = User(username='b', parent=a).save()
    >>> c = User(username='c', parent=a).save()
    >>> for i in User.all():
    ...     print i
    <User {'username':u'a','parent':None,'id':1}>
    <User {'username':u'b','parent':<User {'username':u'a','parent':None,'id':1}>,'id':2}>
    <User {'username':u'c','parent':<User {'username':u'a','parent':None,'id':1}>,'id':3}>
    >>> for i in a.children.all():
    ...     print i
    <User {'username':u'b','parent':<User {'username':u'a','parent':None,'id':1}>,'id':2}>
    <User {'username':u'c','parent':<User {'username':u'a','parent':None,'id':1}>,'id':3}>
    """
    
def test_floatproperty():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     f = FloatProperty()
    >>> Test.f.precision
    10
    >>> class Test1(Model):
    ...     f = FloatProperty(precision=6)
    >>> Test1.f.precision
    6
    >>> class Test2(Model):
    ...     f = FloatProperty(max_length=5)
    >>> Test2.f.precision
    5
    >>> a = Test2(f=23.123456789).save()
    >>> a
    <Test2 {'f':23.123456788999999,'id':1}>
    >>> Test2.get(1)
    <Test2 {'f':23.123456788999999,'id':1}>
    """
    
def test_datetime_property():
    """
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     date1 = DateTimeProperty()
    ...     date2 = DateProperty()
    ...     date3 = TimeProperty()
    >>> a = Test()
    >>> #test common datetime object
    >>> a.date1=datetime.datetime(2009,1,1,14,0,5)
    >>> a.date2=datetime.date(2009,1,1)
    >>> a.date3=datetime.time(14,0,5)
    >>> #test to_dict function
    >>> print a.to_dict()
    {'date1': '2009-01-01 14:00:05', 'date3': '14:00:05', 'date2': '2009-01-01', 'id': None}
    >>> print a.to_dict('date1', 'date2')
    {'date1': '2009-01-01 14:00:05', 'date2': '2009-01-01'}
    >>> print repr(a.date1)
    datetime.datetime(2009, 1, 1, 14, 0, 5)
    >>> print repr(a.date2)
    datetime.date(2009, 1, 1)
    >>> print repr(a.date3)
    datetime.time(14, 0, 5)
    >>> #test saving result
    >>> print a.save()
    <Test {'date1':datetime.datetime(2009, 1, 1, 14, 0, 5),'date2':datetime.date(2009, 1, 1),'date3':datetime.time(14, 0, 5),'id':1}>
    >>> #test to_dict function
    >>> print a.to_dict()
    {'date1': '2009-01-01 14:00:05', 'date3': '14:00:05', 'date2': '2009-01-01', 'id': 1}
    >>> #test different datetime object to diffent datetime property
    >>> a.date2=datetime.datetime(2009,1,1,14,0,5)
    >>> a.date3=datetime.datetime(2009,1,1,14,0,5)
    >>> print repr(a.date2)
    datetime.date(2009, 1, 1)
    >>> print repr(a.date3)
    datetime.time(14, 0, 5)
    >>> #test string format to datetime property
    >>> a.date1 = '2009-01-01 14:00:05'
    >>> a.date2 = '2009-01-01'
    >>> a.date3 = '14:00:05'
    >>> print repr(a.date1)
    datetime.datetime(2009, 1, 1, 14, 0, 5)
    >>> print repr(a.date2)
    datetime.date(2009, 1, 1)
    >>> print repr(a.date3)
    datetime.time(14, 0, 5)
    >>> #test different string format to datetime property
    >>> a.date1 = '2009/01/01 14:00:05'
    >>> a.date2 = '2009-01-01 14:00:05'
    >>> a.date3 = '2009-01-01 14:00:05'
    >>> print repr(a.date1)
    datetime.datetime(2009, 1, 1, 14, 0, 5)
    >>> print repr(a.date2)
    datetime.date(2009, 1, 1)
    >>> print repr(a.date3)
    datetime.time(14, 0, 5)
    """
    
def test_to_dict():
    """
    >>> set_debug_query(True)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> import datetime
    >>> class Test(Model):
    ...     string = StringProperty(max_length=40)
    ...     boolean = BooleanProperty()
    ...     integer = IntegerProperty()
    ...     date1 = DateTimeProperty()
    ...     date2 = DateProperty()
    ...     date3 = TimeProperty()
    ...     float = FloatProperty()
    ...     decimal = DecimalProperty()
    >>> a = Test()
    >>> a.date1=datetime.datetime(2009,1,1,14,0,5)
    >>> a.date2=datetime.date(2009,1,1)
    >>> a.date3=datetime.time(14,0,0)
    >>> a.string = 'limodou'
    >>> a.boolean = True
    >>> a.integer = 200
    >>> a.float = 200.02
    >>> a.decimal = decimal.Decimal("10.2")
    >>> a.to_dict()
    {'date1': '2009-01-01 14:00:05', 'date3': '14:00:00', 'date2': '2009-01-01', 'string': u'limodou', 'decimal': '10.2', 'float': 200.02000000000001, 'boolean': True, 'integer': 200, 'id': None}
    >>> a.save()
    <Test {'string':u'limodou','boolean':True,'integer':200,'date1':datetime.datetime(2009, 1, 1, 14, 0, 5),'date2':datetime.date(2009, 1, 1),'date3':datetime.time(14, 0),'float':200.02000000000001,'decimal':Decimal("10.2"),'id':1}>
    >>> a.to_dict()
    {'date1': '2009-01-01 14:00:05', 'date3': '14:00:00', 'date2': '2009-01-01', 'string': u'limodou', 'decimal': '10.2', 'float': 200.02000000000001, 'boolean': True, 'integer': 200, 'id': 1}
    """
    
def test_match():
    """
    >>> set_debug_query(False)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> c = ['abc', 'def']
    >>> class Test(Model):
    ...     string = StringProperty(max_length=40, choices=c)
    >>> a = Test()
    >>> a
    <Test {'string':u'','id':None}>
    >>> #test the correct assign
    >>> a.string = 'abc'
    >>> #test the error assign
    >>> try:
    ...     a.string = 'aaa'
    ... except Exception, e:
    ...     print e
    Property string is 'aaa'; must be one of ['abc', 'def']
    >>> #test tuple choices
    >>> c = [('abc', 'Prompt'), ('def', 'Hello')]
    >>> Test.string.choices = c
    >>> #test the correct assign
    >>> a.string = 'abc'
    >>> #test the error assign
    >>> try:
    ...     a.string = 'aaa'
    ... except Exception, e:
    ...     print e
    Property string is 'aaa'; must be one of ['abc', 'def']
    """

def test_result():
    """
    >>> db = get_connection('sqlite://')
    >>> db.echo = False
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(CHAR, max_length=20)
    ...     year = Field(int, default=0)
    >>> Test(username='limodou', year=10).save()
    <Test {'username':u'limodou','year':10,'id':1}>
    >>> Test(username='user', year=5).save()
    <Test {'username':u'user','year':5,'id':2}>
    >>> print list(Test.all())
    [<Test {'username':u'limodou','year':10,'id':1}>, <Test {'username':u'user','year':5,'id':2}>]
    >>> print list(Test.filter(Test.c.year > 5))
    [<Test {'username':u'limodou','year':10,'id':1}>]
    >>> print list(Test.all().order_by(Test.c.year.desc()))
    [<Test {'username':u'limodou','year':10,'id':1}>, <Test {'username':u'user','year':5,'id':2}>]
    >>> print list(Test.all().order_by(Test.c.year.asc(), Test.c.username.desc()))
    [<Test {'username':u'user','year':5,'id':2}>, <Test {'username':u'limodou','year':10,'id':1}>]
    >>> print Test.count()
    2
    >>> print Test.filter(Test.c.year>5).count()
    1
    >>> print list(Test.all().values(Test.c.username))
    [(u'limodou',)]
    >>> print Test.all().values_one(Test.c.username)
    (u'limodou',)
    >>> print list(Test.filter(Test.c.year<0))
    []
    >>> print Test.filter(Test.c.year<0).one()
    None
    >>> print Test.filter(Test.c.year>5).one()
    <Test {'username':u'limodou','year':10,'id':1}>
    """
    

#if __name__ == '__main__':
#    set_debug_query(True)
#    db = get_connection('mysql://root:limodou@localhost/test')
#    db.metadata.drop_all()
#    class Test(Model):
#        f = FloatProperty()
#    print Test.f.precision
#    class Test1(Model):
#        f = FloatProperty(precision=6)
#    print Test1.f.precision
#    class Test2(Model):
#        f = FloatProperty(max_length=5)
#    print Test2.f.precision
#    a = Test2(f=23.123456789).save()
#    print a
#    print Test2.get(1)
    
    
    
