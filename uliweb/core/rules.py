from werkzeug.routing import Map, Rule

def Mapping(**kwargs):
    return Map(**kwargs)

def add_rule(map, url, endpoint=None, **kwargs):
    kwargs['endpoint'] = endpoint
    map.add(Rule(url, **kwargs))
            