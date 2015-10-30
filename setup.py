from setuptools import setup, find_packages


setup(
    name='import-parltrack-representatives',
    version='0.0.1',
    description='Import parltrack into django-representatives',
    author='Arnaud Fabre',
    author_email='webmaster@memopol.org',
    url='http://github.com/political-memory/compotista-import_parltrack',
    packages=find_packages(),
    include_package_data=True,
    license='GPLv3',
    keywords='django government parliament',
    install_requires=[
        'ijson',
        'django-representatives>=0.0.1',
    ],
    classifiers=[
        'Development Status :: 1 - Alpha/Planning',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
