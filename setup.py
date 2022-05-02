from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


# Get version
exec(open('src/pybrake/version.py').read())

setup(
    name='pybrake',
    version=version,
    description='Python exception notifier for Airbrake',
    long_description=readme(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development',
    ],
    keywords='airbrake exception error notifier',
    project_urls={
        'Documentation': 'https://airbrake.io',
        'Funding': 'https://airbrake.io',
        'Say Thanks!': 'https://airbrake.io',
        'Source': 'http://github.com/airbrake/pybrake',
        'Tracker': 'http://github.com/airbrake/pybrake/issues',
    },
    url='http://github.com/airbrake/pybrake',
    author='Airbrake Technologies, Inc.',
    author_email='support@airbrake.io',
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['tdigest'],
    tests_require=['tdigest'],
    include_package_data=True,
    zip_safe=False
)
