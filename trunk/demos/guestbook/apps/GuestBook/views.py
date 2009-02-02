#coding=utf-8
from uliweb.core.SimpleFrame import expose

@expose('/')
def index():
    return '<h1>Hello, Uliweb</h1>'

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
        flag = form.check(request.params)
        if flag:
            n = Note(**form.data)
            n.save()
            return redirect(url_for('%s.views.guestbook' % request.appname))
        else:
            message = "There is something wrong! Please fix them."
            return {'form':form, 'message':message}

@expose('/guestbook/delete/<id>')
def del_comment(id):
    from models import Note

    n = Note.get(int(id))
    if n:
        n.delete()
        return redirect(url_for('%s.views.guestbook' % request.appname))
    else:
        error("No such record [%s] existed" % id)
