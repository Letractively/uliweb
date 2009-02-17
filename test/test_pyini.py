from uliweb.utils.pyini import *

def test_sorteddict():
    """
    >>> d = SortedDict()
    >>> d
    <SortedDict {}>
    >>> d.name = 'limodou'
    >>> d['class'] = 'py'
    >>> d
    <SortedDict {'class':'py', 'name':'limodou'}>
    >>> d.keys()
    ['name', 'class']
    >>> d.values()
    ['limodou', 'py']
    >>> d['class']
    'py'
    >>> d.name
    'limodou'
    >>> d.get('name', 'default')
    'limodou'
    >>> d.get('other', 'default')
    'default'
    >>> 'name' in d
    True
    >>> 'other' in d
    False
    >>> print d.other
    None
    >>> try:
    ...     d['other']
    ... except Exception, e:
    ...     print e
    'other'
    >>> del d['class']
    >>> del d['name']
    >>> d
    <SortedDict {}>
    >>> d['name'] = 'limodou'
    >>> d.pop('other', 'default')
    'default'
    >>> d.pop('name')
    'limodou'
    >>> d
    <SortedDict {}>
    >>> d.update({'class':'py', 'attribute':'border'})
    >>> d
    <SortedDict {'attribute':'border', 'class':'py'}>
    """
def test_section():
    """
    >>> s = Section('default', "#comment")
    >>> print s
    #comment
    [default]
    <BLANKLINE>
    >>> s.name = 'limodou'
    >>> s.add_comment('name', '#name')
    >>> s.add_comment(comments='#change')
    >>> print s
    #change
    [default]
    #name
    name = 'limodou'
    <BLANKLINE>
    >>> del s.name
    >>> print s
    #change
    [default]
    <BLANKLINE>
    """
    
def test_ini():
    """
    >>> x = Ini()
    >>> x['default'] = Section('default', "#comment")
    >>> x.default.name = 'limodou'
    >>> x.default['class'] = 'py'
    >>> x.default.list = ['abc']
    >>> print x
    #coding=utf-8
    #comment
    [default]
    name = 'limodou'
    class = 'py'
    list = ['abc']
    <BLANKLINE>
    >>> x.default.list = ['cde'] #for mutable object will merge the data, including dict type
    >>> print x.default.list
    ['cde', 'abc']
    >>> x.default.d = {'a':'a'}
    >>> x.default.d = {'b':'b'}
    >>> print x.default.d
    {'a': 'a', 'b': 'b'}
    """  