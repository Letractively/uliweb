#coding=utf-8
import time, sys
sys.path.insert(0, '../uliweb/lib')
from uliweb.orm import *

#basic testing
def test_1():
    """
    >>> set_auto_bind(True)
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
    >>> set_auto_bind(True)
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
    >>> set_auto_bind(True)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    >>> class Test1(Model):
    ...     test = Reference(Test)
    ...     name = Field(str)
    >>> a1 = Test(username='limodou1').save()
    >>> a2 = Test(username='limodou2').save()
    >>> a3 = Test(username='limodou3').save()
    >>> b1 = Test1(name='zoom', test=a1).save()
    >>> b2 = Test1(name='aaaa', test=a1).save()
    >>> b3 = Test1(name='bbbb', test=a2).save()
    >>> a1
    <Test {'username':'limodou1','year':0,'id':1}>
    >>> list(a1.test1_set.all())[0]
    <Test1 {'test':<Test {'username':'limodou1','year':0,'id':1}>,'name':'zoom','id':1}>
    >>> a1.test1_set.count()
    2
    >>> b1.test
    <Test {'username':'limodou1','year':0,'id':1}>
    >>> a1.username = 'zoom'
    >>> Test.get(1)
    <Test {'username':'limodou1','year':0,'id':1}>
    >>> x = a1.save()
    >>> Test.get(1)
    <Test {'username':'zoom','year':0,'id':1}>
    """
    
#testing many2one using collection_name
def test_4():
    """
    >>> set_auto_bind(True)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    >>> class Test1(Model):
    ...     test = Reference(Test, collection_name='tttt')
    ...     name = Field(str)
    >>> a1 = Test(username='limodou1').save()
    >>> b1 = Test1(name='zoom', test=a1).save()
    >>> b2 = Test1(name='aaaa', test=a1).save()
    >>> a1
    <Test {'username':'limodou1','year':0,'id':1}>
    >>> list(a1.tttt.all())[0]   #here we use tttt but not test1_set
    <Test1 {'test':<Test {'username':'limodou1','year':0,'id':1}>,'name':'zoom','id':1}>
    >>> a1.tttt.count()
    2
    >>> b3 = Test1(name='aaaa').save()
    >>> a1.tttt.count()
    2
    >>> b3.test = a1
    >>> b3.save()
    <Test1 {'test':<Test {'username':'limodou1','year':0,'id':1}>,'name':'aaaa','id':3}>
    >>> Test1.get(3)
    <Test1 {'test':<Test {'username':'limodou1','year':0,'id':1}>,'name':'aaaa','id':3}>
    """
    
#testing transaction
def test_5():
    """
    >>> set_auto_bind(True)
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
    >>> set_auto_bind(True)
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> class Test(Model):
    ...     username = Field(str)
    ...     year = Field(int)
    >>> class Test1(Model):
    ...     test = OneToOne(Test)
    ...     name = Field(str)
    >>> a1 = Test(username='limodou1').save()
    >>> b1 = Test1(name='zoom', test=a1).save()
    >>> a1
    <Test {'username':'limodou1','year':0,'id':1}>
    >>> a1.test1
    <Test1 {'test':<Test {'username':'limodou1','year':0,'id':1}>,'name':'zoom','id':1}>
    >>> b1.test
    <Test {'username':'limodou1','year':0,'id':1}>
    """
    
#test ManyToMany
def test_7():
    import interlude
    """
    >>> set_auto_bind(True)
    >>> set_debug_query(True)
    >>> db = get_connection('sqlite://')
    >>> class User(Model):
    ...     username = Field(unicode)
    >>> class Group(Model):
    ...     name = Field(str)
    ...     users = ManyToMany(User)
    >>> a = User(username='limodou').save()
    >>> b = User(username='zoom').save()
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
    [<User {'username':u'limodou','id':1}>, <User {'username':u'zoom','id':2}>, <User {'username':u'abc','id':3}>]
    >>> g1.users.delete(a)
    >>> g1.users.clear()
    >>> g1.users.count()
    0
    >>> g1.users.add(a, b, c)
    >>> g2.users.add(a)
    >>> list(a.group_set.all())
    [<Group {'name':'python','id':1}>, <Group {'name':'perl','id':2}>]
    >>> a.group_set.add(g3)
    >>> list(a.group_set.all())
    [<Group {'name':'python','id':1}>, <Group {'name':'perl','id':2}>, <Group {'name':'java','id':3}>]
    >>> g1.users.delete(a)
    >>> list(g1.users.all())
    [<User {'username':u'zoom','id':2}>, <User {'username':u'abc','id':3}>]
    >>> list(g2.users.all())
    [<User {'username':u'limodou','id':1}>]
    >>> list(a.group_set.all())
    [<Group {'name':'perl','id':2}>, <Group {'name':'java','id':3}>]
    """
