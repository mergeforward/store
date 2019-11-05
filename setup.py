from setuptools import setup

docs = """
store
-------------

simple storage library
"""

setup(
    version='2019.11.03',
    name='store',
    url='https://github.com/mergeforward/store.git',
    license='MIT',
    author='dameng',
    author_email='pingf0@gmail.com',
    description='simple storage library',
    long_description=docs,
    # py_modules=['store', 'store.contrib', 'store.contrib.factory'],
    # if you would be using a package instead use packages instead
    # of py_modules:
    packages=['store', 'store.contrib', 'store.contrib.factory'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'pony'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
