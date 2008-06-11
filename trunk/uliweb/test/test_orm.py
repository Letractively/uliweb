import time, sys
sys.path.insert(0, '..')

print 'import...', time.time()
from utils.orm import *
import geniusql
print 'end import...', time.time()

def show(tablename):
    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    schema = db._schema
    t = schema.discover(tablename)
    
    for k, v in t.items():
        print k, v
        
    print t.select_all()
    
def clear(table):
    table.delete_all()
    
def test1():
    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    
    class Test(Model):
        username = Field(str)
        year = Field(int)
        
    b = Test.insert(username='limodou')
    print Test.select_all()
    print b
    
    
def test2():
    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    class Test(Model):
        username = Field(str)
        year = Field(int)
        
    print Test.select_all()
        
    class Test(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        name = Field(str, max_length=65536)
        
    show('test')
    
def test3():
    clear_other()
    import decimal

#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite://test.db')
    print 'begin', time.time()
    class Other(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        salery = Field(decimal.Decimal, max_length=16)
        
    def insert(n=10):
        for i in range(n):
            Other.insert(username='limodou', salery=12.3+i)
            time.sleep(0.01)
    import thread
    thread.start_new_thread(insert, ())
    thread.start_new_thread(insert, ())
    print 'end', time.time()
    
    time.sleep(5)
            
    show('other')

def test4():
    clear_other()
    import decimal
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite://test.db')
    print 'begin', time.time()
    schema = db._schema
    Other = schema.table('other')
    Other['username'] = schema.column(str, hints={'bytes':20})
    Other['year'] = schema.column(int)
    Other['salery'] = schema.column(decimal.Decimal, hints={'precision':16})
    
    def insert(n=10):
        for i in range(n):
            Other.insert(username='limodou', salery=12.3+i)
            time.sleep(0.01)
    import thread
    thread.start_new_thread(insert, ())
    thread.start_new_thread(insert, ())
    print 'end', time.time()
    
    time.sleep(5)
            
    show('other')
    
def test5():
    import decimal

#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    db = get_connection('sqlite://test.db')
    class Other(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        salery = Field(decimal.Decimal, max_length=16)
        
#    show('other')
    Other.bind()
    print list(db.select((Other.table, ['username'])))

def test6():
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_auto_bind(True)
    set_auto_migirate(True)
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

    a = A.insert(username='limodou', year='35')
    a = A.insert(username='zoom', year='30')
    b = B.insert(a_id=a.id, name='lost')
    print A.select_all()
    print B.select_all()
    print list(db.select((A & B, [A.keys(), B.keys()])))
    print list(db.select((A << B, [A.keys(), B.keys()])))

def test7():
#    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    set_auto_bind(True)
    set_auto_migirate(True)
    db = get_connection('sqlite')
    db.create()

    class A(Model):
        username = Field(str, max_length=20)
        year = Field(int)

    class B(Model):
        a_id = Reference(A)
        name = Field(str)
        
    a = A.insert(username='limodou', year='35')
    a = A.insert(username='zoom', year='30')
    b = B.insert(a_id=a.id, name='lost')
    print A.select_all()
    print B.select_all()
    print list(db.select((A & B, [A.keys(), B.keys()])))
    print list(db.select((A << B, [A.keys(), B.keys()])))

def clear_other():
    import decimal
    db = get_connection('mysql://localhost/test', user='root', passwd='limodou')
    class Other(Model):
        username = Field(str, max_length=20)
        year = Field(int)
        salery = Field(decimal.Decimal, max_length=16)
    Other.delete_all()
    
if __name__ == '__main__':
    test7()
