#coding=utf-8
import time, sys
sys.path.insert(0, '../uliweb/lib')
from uliweb.orm import *

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
    """
