def message(msg, type='error', theme='clean'):
    """
    type can be 'error', 'ok'
    theme can be 'clean', 'solid', 'round', 'tooltip', 'icon'
    """
    if theme == 'round':
        return """<div class="message-container">
    <div class="message %(theme)s %(type)s">
      <div>%(msg)s</div>
    </div>
</div>""" % locals()
    else:
        return """<div class="message-container">
    <div class="message %(theme)s %(type)s">%(msg)s</div>
</div>""" % locals()

def round_box(title, content, width=400):
    if isinstance(width, int):
        width = "%dpx" % width
    if not width.endswith('px'):
        width = width + 'px'
    return """<div class="cssbox" style="width:%(width)s;">
      <div class="cssbox_head"><h2>%(title)s</h2></div>
      <div class="cssbox_body">%(content)s
      </div>
    </div>""" % locals()