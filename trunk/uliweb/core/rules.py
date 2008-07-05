from werkzeug.routing import Map, Rule
_static_views = []

def Mapping(**kwargs):
    return Map(**kwargs)

def add_rule(map, url, endpoint=None, **kwargs):
    kwargs['endpoint'] = endpoint
    static = kwargs.pop('static', None)
    if static:
        _static_views.append(kwargs['endpoint'])
    map.add(Rule(url, **kwargs))
            