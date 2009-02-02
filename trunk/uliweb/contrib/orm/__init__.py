from uliweb.core.plugin import plugin

@plugin('startup')
def startup(sender):
    from uliweb import orm
    
    orm.set_debug_query(sender.settings.ORM.DEBUG_LOG)
    orm.set_auto_bind(sender.settings.ORM.AUTO_BIND)
    orm.get_connection(sender.settings.ORM.CONNECTION)
