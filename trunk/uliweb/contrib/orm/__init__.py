from uliweb.core.dispatch import bind
import uliweb

@bind('startup')
def startup(sender):
    from uliweb import orm
    
    orm.set_debug_query(sender.settings.ORM.DEBUG_LOG)
    orm.set_auto_create(sender.settings.ORM.AUTO_CREATE)
    orm.get_connection(sender.settings.ORM.CONNECTION)

    if 'MODELS' in uliweb.settings:
        for k, v in uliweb.settings.MODELS.items():
            orm.set_model(v, k)