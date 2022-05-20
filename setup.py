from os import path
from setuptools import setup, find_packages

base_dir = path.abspath(path.dirname(__file__))

with open(path.join(base_dir, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='FirebaseData',
    version='0.6.3',
    packages=find_packages(),
    install_requires=[
        'blinker>=1.4',
    ],
    python_requires='>=3, <4',
    url='https://github.com/heston/firebase-live-data',
    author='Heston Liebowitz',
    description=(
        'Utilities for storing, retrieving, and monitoring Firebase Realtime '
        'Database objects in Python.'
    ),
    long_description=long_description,
    license='MIT'
)
