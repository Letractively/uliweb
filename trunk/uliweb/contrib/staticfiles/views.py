from uliweb.core.SimpleFrame import static_serve

def static(filename):
    return static_serve(application, filename)
