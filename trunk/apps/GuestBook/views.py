#coding=utf-8
from uliweb.core.SimpleFrame import expose

from uliweb.core.SimpleFrame import static_serve
@expose('/static/<regex(".*$"):filename>')
def static(filename):
    return static_serve(request, filename)

@expose('/guestbook')
def guestbook():
    from models import Note
    
    notes = Note.filter(order=lambda z: [reversed(z.datetime)])
    return locals()
      
@expose('/guestbook/new_comment')
def new_comment():
    from models import Note
    from forms import NoteForm
    import datetime
    
    form = NoteForm()
    if request.method == 'GET':
        return {'form':form.html(), 'message':''}
    elif request.method == 'POST':
        flag, data = form.validate(request.params)
        if flag:
            data['datetime'] = datetime.datetime.now()
            n = Note(**data)
            n.put()
            redirect(url_for('%s.views.guestbook' % request.appname))
        else:
            message = "There is something wrong! Please fix them."
            return {'form':form.html(request.params, data, py=False), 'message':message}
    
@expose('/guestbook/delete/<id>')
def del_comment(id):
    from models import Note

    n = Note.get(int(id))
    if n:
        n.delete()
        redirect(url_for('%s.views.guestbook' % request.appname))
    else:
        error("No such record [%s] existed" % id)