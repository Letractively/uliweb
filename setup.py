import uliweb
from setuptools import setup

setup(name='uliweb',
      version=uliweb.version,
      description="Easy python web framework",
      long_description=uliweb.__doc__,
      classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GPLv2 License",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Framework",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
      ],
      packages = ['uliweb'],
      install_requires = ['WebOb', 'simplejson', 'SQLAlchemy'],
      platforms = 'any',
      keywords='wsgi web framework',
      author=uliweb.author,
      author_email=uliweb.author_email,
      url=uliweb.url,
      license=uliweb.license,
      include_package_data=True,
      zip_safe=False,
      entry_points = {
          'console_scripts': [
              'uliweb = uliweb.manage:main',
          ],
      },
      
      )
