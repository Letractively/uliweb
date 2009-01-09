import messages

class ValidationError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)

def __get_choices_keys(choices):
    if isinstance(choices, dict):
        keys = set(choices.keys())
    elif isinstance(choices, (list, tuple)):
        keys = set([])
        for v in choices:
            if isinstance(v, (list, tuple)):
                keys.add(v[0])
            else:
                keys.add(v)
    else:
        raise ValidationError, messages.choice_datatype_error
    return keys
    
def IS_IN_SET(choices):
    '''
    choices should be a list or a tuple, e.g. [1,2,3]
    '''
    def f(data):
        if data not in __get_choices_keys(choices):
            raise ValidationError, messages.is_in_set_validate_error
    return f

