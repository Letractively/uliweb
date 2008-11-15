import uliweb.core.js as js

class JxLib(js.Snippet):
    jslink = ['jxlib/jxlib.js']
    _csslink = 'jxlib/themes/%s/jxtheme.css'
    
    def __init__(self, theme='crispin'):
        if theme not in ['crispin', 'delicious']:
            theme = 'crispin'
        self.theme = theme
        JxLib.csslink = JxLib._csslink % self.theme
    
    def image(self, filename):
        return 'jxlib/theme/%s/images/%s' % (self.theme, filename)