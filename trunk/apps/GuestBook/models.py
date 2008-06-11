from utils.orm import *
import datetime

class Note(Model):
    username = Field(str)
    message = Field(str, max_length=1024)
    homepage = Field(str)
    email = Field(str)
    datetime = Field(datetime.datetime)
    
