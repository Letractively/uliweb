from uliweb.core.js import Snippet

class Message(Snippet):
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
   
class RoundBox(Snippet):
    jslink = ['js/jquery.js', 'widgets/boxes/js/jq.boxes.js']
    csslink = 'widgets/boxes/css/boxes.css'
    
    js = """$(function(){
	$('.boxes').boxes();
});"""
    
    def __init__(self, content):
        self.content = content
        
    def render(self):
        return """<div class="boxes">
%s
</div> 
""" % self.content
        
