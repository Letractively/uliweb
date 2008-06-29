#coding=utf-8
import time, sys

from orm import *

def test1():
    set_auto_bind(True)
    set_auto_migrate(True)
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite://')
    
    class Test(Model):
        username = Field(unicode)
        year = Field(int, default=0)
        
    print dir(Test), Test.metadata
    Test(username='limodou').save()
    Test(username='limodou1').save()
    b = Test(username=u'中文').save()
    print list(Test.all())
    print b, type(b.username), b.username.encode('gbk')
    b.delete()
    print list(Test.filter())
    Test.remove(Test.c.username==u'limodou')
    print list(Test.all())
    
    
def test2():
    set_debug_query(True)
    set_auto_bind(True)
    set_auto_migrate(True)
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite://')
    class Test(Model):
        username = Field(str)
        year = Field(int)
        name = Field(str, max_length=65536)
        
    Test(username='limodou').save()
    show('test')
        
    class Test(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        
    show('test')
    
def test3():
    import decimal

#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_auto_bind(True)
    set_auto_migrate(True)
    db = get_connection('sqlite')
    print 'begin', time.time()
    class Other(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        salery = Field(decimal.Decimal, max_length=16)
        
    def insert(n=10):
        for i in range(n):
            Other(username='limodou', salery=decimal.Decimal('12.3')+i).save()
            time.sleep(0.01)
    import thread
    thread.start_new_thread(insert, ())
    thread.start_new_thread(insert, ())
    print 'end', time.time()
    
    time.sleep(5)
            
    show('other')

def test4():
    import decimal
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite')
    print 'begin', time.time()
    schema = db._schema
    Other = schema.table('other')
    Other['username'] = schema.column(str, hints={'bytes':20})
    Other['year'] = schema.column(int)
    Other['salery'] = schema.column(decimal.Decimal, hints={'precision':16})
    
    def insert(n=10):
        for i in range(n):
            Other.insert(username='limodou', salery=decimal.Decimal('12.3')+i)
            time.sleep(0.01)
    import thread
    thread.start_new_thread(insert, ())
    thread.start_new_thread(insert, ())
    print 'end', time.time()
    
    time.sleep(5)
            
    show('other')
    
def test5():
    import decimal
    set_auto_bind(True)
    set_auto_migrate(True)
    set_debug_query(True)

    from geniusql import logic, logicfuncs
    logicfuncs.init()
    
    print logic.Expression(lambda x:x.id in [1,2])
    
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite')
    class Other(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        
    Other(username='limodou', year=1).save()
    Other(username='zoom', year=2).save()
#    print list(db.select((Other.table, ['username'])))
    print list(Other.table.select_all(lambda x:x.id in [1]))

def test6():
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_auto_bind(True)
    set_auto_migrate(True)
    db = get_connection('sqlite')
    db.create()

    class A(Model):
        username = Field(str, max_length=20)
        year = Field(int)

    class B(Model):
        a_id = Field(int)
        name = Field(str)
        
#    A.bind(auto_create=True)
#    B.bind(auto_create=True)
    
    B.table.references['a'] = ('a_id', A.tablename, 'id')
#    show('other')

    a = A(username='limodou', year='35').save()
    a = A(username='zoom', year='30').save()
    b = B(a_id=a.id, name='lost').save()
    print list(A.filter())
    print list(B.filter())
    print list(db.select((A.table & B.table, [A.properties.keys(), B.properties.keys()])))
    print list(db.select((A.table << B.table, [A.properties.keys(), B.properties.keys()])))

def test7():
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_auto_bind(True)
    set_auto_migrate(True)
    set_debug_query(True)
    db = get_connection('sqlite')
    db.create()

    class A(Model):
        username = Field(str, max_length=20)
        year = Field(int)

    class B(Model):
        a_id = Reference(A)
        name = Field(str)
        
    a1 = A(username='limodou', year='35').save()
    a2 = A(username='zoom', year='30').save()
    b = B(a_id=a1, name='lost').save()
    print '1', list(A.filter())
    print '2', list(B.filter())
    print '3', b.a_id
    b = B(a_id=a2.id, name='lost').save()
    print '4', b.a_id
    b = B.get(2)
    print '5', b.a_id
    print '6', b.a_id
    print '7', list(a1.b_set)
#    print list(db.select((A & B, [A.keys(), B.keys()])))
#    print list(db.select((A << B, [A.keys(), B.keys()])))

def test8():
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_auto_bind(True)
    set_auto_migrate(True)
    db = get_connection('sqlite')
    db.create()

    class A(Model):
        username = Field(str, max_length=20)
        year = Field(int)

    a = A.insert(username='limodou', year='35')
    a = A.insert(username='zoom', year='30')
    a = A.insert(username='limodou', year='25')
    
    print A.select_all(order=lambda x: [x.username, x.year])

def test9():
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_debug_query(False)
    set_auto_bind(True)
    set_auto_migrate(True)
    db = get_connection('sqlite')
    db.create()

    class A(Model):
        username = Field(str, max_length=20)
        year = Field(int)

    class B(Model):
        a = Reference(A)
        name = Field(str)
        
    a = A.insert(username='limodou', year='35')
    a = A(username='zoom', year='30')
    a.put()
    b = B.insert(a=a.id, name='lost')
    b = B.insert(a=a.id, name='tttt')
    b = B(a=a.id, name='world')
    b.put()
#    b = B(a=a, name='ttttt')
#    b.put()

#    print A.select_all()
#    print B.select_all()
#    print '-----------------'
    print list(a.reference(B))
    print list(a.reference_a(B))
    print list(b.reference(A))
    c = b.foreign(A)
    print c
    c.username += '_fix'
    c.put()
    print c
#    print list(db.select((B & A, [B.keys(), A.keys()])))
#    print list(db.select((A << B, [A.keys(), B.keys()])))

def test10():
    def _log(message):
        print message
        
    db = geniusql.db('sqlite', name=':memory:')
    db.log = _log
    db.create()
    schema = db.schema()
    schema.create()
    
    A = schema.table('a')
    A['id'] = schema.column(int, autoincrement=True, key=True)
    A['name'] = schema.column(str)
    schema['a'] = A
    
    B = schema.table('b')
    B['id'] = schema.column(int, autoincrement=True, key=True)
    B['a_id'] = schema.column(int)
    B['b_id'] = schema.column(int)
    B['message'] = schema.column(str)
    schema['B'] = B
    B.references['r1'] = ('a_id', 'a', 'id')
    B.references['r2'] = ('b_id', 'a', 'id')
    
    a = A.insert(name='limodou')
    b = A.insert(name='zoom')
    B.insert(a_id=a['id'], message='111111')
    B.insert(b_id=b['id'], message='222222')
    
    print list(B.select_all())
#    print db.select((A, ['name']))
    print list(db.select((A&B, [A.keys(), B.keys()], lambda x, y:y.a_id==1)))
    
if __name__ == '__main__':
    test1()
