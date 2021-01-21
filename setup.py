from setuptools import setup


def readme():
  with open('README.md') as f:
    return f.read()


# Get version
exec(open('pybrake/version.py').read())


setup(name='pybrake',
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
        'Topic :: Software Development',
      ],
      keywords='airbrake exception error notifier',
      url='http://github.com/airbrake/pybrake',
      author='Vladimir Mihailenco',
      author_email='vlad@airbrake.io',
      license='MIT',
      packages=['pybrake'],
      install_requires=['tdigest'],
      tests_require=['tdigest'],
      include_package_data=True,
      zip_safe=False)
