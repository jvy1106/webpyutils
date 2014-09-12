from setuptools import setup

setup(name='webpyutils',
    version='0.0.1',
    description='web.py utilities to build quick RESTful API Services',
    author='Jesse Yen',
    author_email='jesse@jads.com',
    url='',
    install_requires=[
        'DBUtils',
        'web.py',
        'flup',
        'argparse',
    ],  
    packages=[
        'webpyutils',
    ],  

    #entry_points={'console_scripts': [
    #    'server = webpyutils.api:main',
    #]},
)
