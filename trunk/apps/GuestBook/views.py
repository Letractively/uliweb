#coding=utf-8
from frameworks.SimpleFrame import expose

@expose('/guestbook')
def guestbook():
    from models import Note
    
    notes = Note.select_all()
    print notes
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
            Note.insert(**data)
            redirect(url_for('%s.views.guestbook' % request.appname))
        else:
            message = "There is something wrong! Please fix them."
            return {'form':form.html(request.params, data, py=False), 'message':message}
    