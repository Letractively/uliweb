def startup_installed(sender):
    from uliweb.core import template
    from tags import LinkNode, UseNode
    
    if sender.settings.TEMPLATE.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.TEMPLATE.TEMPLATE_TEMP_DIR)
        
    template.register_node('link', LinkNode)
    template.register_node('use', UseNode)
    
    template.BEGIN_TAG = sender.settings.TEMPLATE.BEGIN_TAG
    template.END_TAG = sender.settings.TEMPLATE.END_TAG
