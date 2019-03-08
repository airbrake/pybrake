from setuptools import setup


def content_of(file_name):
  with open(file_name) as f:
    return f.read()


# Get version
execfile('pybrake/version.py')

setup(name='pybrake',
      version=version,
      description='Python exception notifier for Airbrake',
      long_description=content_of('README.md'),
      long_description_content_type='text/markdown',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
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
