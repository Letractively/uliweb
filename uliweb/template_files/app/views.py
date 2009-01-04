#coding=utf-8
from uliweb.core.SimpleFrame import expose

@expose('/')
def index():
    return '<h1>Hello, Uliweb</h1>'
