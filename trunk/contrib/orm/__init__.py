from uliweb.core.plugin import plugin

@plugin('startup')
def startup(sender):
    """
    @ORM_DEBUG_LOG default=False
    @ORM_CONNECTION default={'connection':'sqlite:///test.db'}
    @ORM_AUTO_BIND default=True
    @ORM_AUTO_MIGRATE default=True
    """
    from uliweb import orm
    
    orm.set_debug_query(sender.settings.get('ORM_DEBUG_LOG', False))
    orm.set_auto_bind(sender.settings.get('ORM_AUTO_BIND', True))
    orm.set_auto_migrate(sender.settings.get('ORM_AUTO_MIGRATE', True))
    orm.get_connection(**sender.settings.get('ORM_CONNECTION', {'connection':'sqlite:///test.db'}))
