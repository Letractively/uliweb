def call(app, var, env):
    return {'bottomlinks':'{{=url_for_static("haml-forms.css")}}'}
