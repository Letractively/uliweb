from uliweb.orm import *
import datetime

class Note(Model):
    username = Field(str)
    message = Field(text)
    homepage = Field(str)
    email = Field(str)
    datetime = Field(datetime.datetime, auto_now_add=True)
