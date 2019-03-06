from setuptools import setup

import pybrake


def readme():
  with open('README.md') as f:
    return f.read()


setup(name='pybrake',
      version=pybrake.__version__,
      description='Python exception notifier for Airbrake',
      long_description=readme(),
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
      setup_requires=[],
      tests_require=[],
      include_package_data=True,
      zip_safe=False)
