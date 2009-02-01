# How to test it?
# easy_install nose
# cd test
# nosetests test_form.py --with-doctest

from uliweb.lib.webob import Request
from uliweb.form import *

def test_form():
    """
    >>> class F(Form):
    ...     title = StringField(label='Title:', required=True, help_string='Title help string')
    ...     content = TextField(label='Content:')
    >>> f = F()
    >>> print f
    <form action="" class="form" method="post" enctype="multipart/form-data">
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
    <input name="title" type="text" class="field" value="" id="field_title"></input>
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
    <textarea class="field" rows="5" cols="40" name="content" id="field_content"></textarea>
    </td>
    <td></td>
    </tr>
    <tr>
    <td colspan="3" class="buttons">
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
    """
