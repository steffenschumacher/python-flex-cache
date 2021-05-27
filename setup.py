from setuptools import setup, find_packages

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='python-flex-cache',
      version='0.1.5',
      description='Basic Redis/Disk/Memory caching for functions',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='http://github.com/steffenschumacher/python-flex-cache',
      author='Steffen Schumacher (forked from python-redis-cache // Taylor Hakes)',
      license='MIT',
      python_requires='>=3.6',
      packages=find_packages(),
      setup_requires=['pytest-runner==5.2', 'diskcache==5.2.1'],
      tests_require=['pytest==5.4.3', 'redis==3.5.3'],
)
