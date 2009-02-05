# How to test it?
# easy_install nose
# cd test
# nosetests test_form.py --with-doctest
import time, sys
sys.path.insert(0, '../uliweb/lib')

from webob import Request
from uliweb.form import *

def test_1():
    """
    >>> class F(Form):
    ...     title = StringField(label='Title:', required=True, help_string='Title help string')
    ...     content = TextField(label='Content:')
    >>> f = F()
    >>> print f
    <form class="form" action="" enctype="multipart/form-data" method="post">
    <table>
    <tbody>
    <tr>
    <td>
    <label for="field_title">
    Title:<span class="field_required">
    (*)
    </span>
    </label>
    </td>
    <td>
    <input class="field" id="field_title" name="title" type="text" value=""></input>
    </td>
    <td>
    Title help string
    </td>
    </tr>
    <tr>
    <td>
    <label for="field_content">
    Content:
    </label>
    </td>
    <td>
    <textarea class="field" cols="40" id="field_content" name="content" rows="5"></textarea>
    </td>
    <td></td>
    </tr>
    <tr>
    <td class="buttons" colspan="3">
    <input type="submit" value="Submit"></input>
    <input type="reset" value="Reset"></input>
    </td>
    </tr>
    </tbody>
    </table>
    </form>
    >>> req = Request.blank('/test?title=&content=')
    >>> f.check(req.GET)
    False
    >>> req = Request.blank('/test?title=Hello&content=')
    >>> f.check(req.GET)
    True
    >>> req = Request.blank('/test?title=Hello&content=aaaa')
    >>> f.check(req.GET)
    True
    >>> f.title.data
    'Hello'
    >>> f.title.data = 'limodou'
    >>> f.title.html
    '<input class="field" id="field_title" name="title" type="text" value="limodou"></input>'
    >>> F.title.html()
    '<input class="field" id="field_title" name="title" type="text" value=""></input>'
    """

def test_2():
    """
    >>> buf = Buf()
    >>> buf << Tag('div') << Tag('p', 'hello')
    >>> print buf
    <div>
    <p>
    hello
    </p>
    </div>
    
    """
    
def test_3():
    class F(Form):
        title = StringField(label='Title:', required=True, help_string='Title help string')
        content = TextField(label='Content:')
    f = F(title='Test form')
    f.layout_class = CSSLayout
    print f
    
if __name__ == '__main__':
    test_3()
