from setuptools import setup, find_packages

setup(
    name='FirebaseData',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'blinker>=1.4',
    ],
    author='Heston Liebowitz',
    author_email='me@hestonliebowitz.com',
    description='Utilities for storing, retrieving, and monitoring Firebase Realtime Database objects in Python.',
    license='MIT'
)
