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
    url='http://github.com/airbrake/pybrake',
    author='Vladimir Mihailenco',
    author_email='vlad@airbrake.io',
    license='MIT',
    # packages=find_packages(),
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['tdigest'],
    tests_require=['tdigest'],
    include_package_data=True,
    zip_safe=False
)
