from setuptools import setup

import pybrake


def readme():
  with open('README.rst') as f:
    return f.read()


setup(name='pybrake',
      version=pybrake.__version__,
      description='Python exception notifier for Airbrake',
      long_description=readme(),
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
      install_requires=[],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      include_package_data=True,
      zip_safe=False)
