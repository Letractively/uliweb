import uliweb.core.js as js

class Mootools(js.Snippet):
    jslink = ['mootools/mootools.js']
    
class JxLib(js.Snippet):
    jslink = ['mootools/mootools.js', 'mootools/jxlib/jxlib.standalone.js']
    _csslink = 'mootools/jxlib/themes/%s/jxtheme.css'
    
    def __init__(self, theme='crispin'):
        if theme not in ['crispin', 'delicious']:
            theme = 'crispin'
        self.theme = theme
        JxLib.csslink = JxLib._csslink % self.theme
    
    def image(self, filename):
        return 'jxlib/theme/%s/images/%s' % (self.theme, filename)
