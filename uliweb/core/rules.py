from werkzeug.routing import Map, Rule

from werkzeug.routing import BaseConverter
class RegexConverter(BaseConverter):
    """
    Matches regular expression::

        Rule('/<regex("pattern"):argu_name>')
    """

    def __init__(self, map, *items):
        BaseConverter.__init__(self, map)
        self.regex = items[0]

def Mapping(**kwargs):
    return Map(converters={'regex':RegexConverter}, **kwargs)

def add_rule(map, url, endpoint=None, **kwargs):
    kwargs['endpoint'] = endpoint
    map.add(Rule(url, **kwargs))
            