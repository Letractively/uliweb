import uliweb.core.js as js

class Message(js.Snippet):
    """
    type can be 'error', 'ok'
    theme can be 'clean', 'solid', 'round', 'tooltip', 'icon'
    """
    csslink='widgets/messages/css/messages.css'

    def __init__(self, msg, type='error', theme='clean'):
        self.msg = msg
        self.type = type
        self.theme = theme
        
    def render(self):
        if self.theme == 'round':
            return """<div class="message-container">
    <div class="message %(theme)s %(type)s">
      <div>%(msg)s</div>
    </div>
</div>
""" % self.__dict__
        else:
            return """<div class="message-container">
    <div class="message %(theme)s %(type)s">%(msg)s</div>
</div>
""" % self.__dict__
   
class RoundBox(js.Snippet):
    jslink = ['js/jquery.js', 'widgets/boxes/js/jq.boxes.js']
    csslink = 'widgets/boxes/css/boxes.css'
    
    js = """$(function(){
	$('.boxes').boxes();
});"""
    
class NiceEditor(js.Snippet):
    jslink = 'widgets/nicEdit/js/nicEdit.js'
    
    def __init__(self, id=None, config=None):
        self.config = config or {'fullPanel':True}
        self.id = id
        
    def render(self):
        s = js.Script()
        if self.config:
            args = self.config
        else:
            args = {}
        args['iconsPath'] = self.htmlbuf.static_file('widgets/nicEdit/nicEditorIcons.gif')
        if not self.id:
            s << "bkLib.onDomLoaded(function() { nicEditors.allTextAreas(%s) });" % args
        else:
            s << """bkLib.onDomLoaded(function() {
new nicEditor(%s).panelInstance('%s');
});""" % (js.S(args), self.id)
        return str(s)