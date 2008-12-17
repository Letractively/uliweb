import uliweb
from setuptools import setup, find_packages

setup(name='uliweb',
      version=uliweb.version,
      description="Easy python web framework",
      long_description="""\
Uliweb is a new brand Python Web Framework. Before creating this framework, 
I've learned and used many frameworks, Karrigell, Cherrypy, Django, web2py, 
but more or less they are not fully satisfy me. So I decide to create myself 
web framework, I hope I can merge their advantages into Uliweb, and I'll try 
to make it simple and easy to use.

This project is created and leaded by Limodou <limodou@gmail.com>. And it has 
received many helps from many kind people.""",
      classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GPLv2 License",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
      ],
      packages = find_packages(),
      install_requires = ['WebOb', 'simplejson', 'SQLAlchemy'],
      platforms = 'any',
      keywords='wsgi web framework',
      author='limodou',
      author_email='limodou@gmail.com',
      url='http://code.google.com/p/uliweb/',
      license='GPLv2',
      include_package_data=True,
      zip_safe=False,
      entry_points = {
          'console_scripts': [
              'uliweb = uliweb.manage:main',
          ],
      },
      
      )
