#coding=utf-8
from uliweb.core.SimpleFrame import expose

from uliweb.core.SimpleFrame import static_serve
@expose('/static/<path:filename>', static=True)
def static(filename):
    return static_serve(request, filename)

@expose('/guestbook')
def guestbook():
    from models import Note
    from sqlalchemy import desc
    
    notes = Note.filter(order_by=[desc(Note.c.datetime)])
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
            n = Note(**data)
            n.put()
            return redirect(url_for('%s.views.guestbook' % request.appname))
        else:
            message = "There is something wrong! Please fix them."
            return {'form':form.html(request.params, data, py=False), 'message':message}
    
@expose('/guestbook/delete/<id>')
def del_comment(id):
    from models import Note

    n = Note.get(int(id))
    if n:
        n.delete()
        return redirect(url_for('%s.views.guestbook' % request.appname))
    else:
        error("No such record [%s] existed" % id)