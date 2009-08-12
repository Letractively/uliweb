def call(app, var, env, version='1.2.3', more=True):
    a = []
    a.append('{{=url_for_static("mootools/mootools-%s-core.js")}}' % version)
    if more:
        a.append('{{=url_for_static("mootools/mootools-%s-more.js")}}' % version)
    return {'toplinks':a}
