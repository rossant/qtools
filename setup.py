import os
try:
    from setuptools import setup 
except ImportError:
    from distutils.core import setup

LONG_DESCRIPTION = \
"""Python tools for Qt."""

if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

if __name__ == '__main__':

    setup(
        name='qtools',
        version='0.1.0.dev',  # alpha pre-release
        author='Cyrille Rossant',
        author_email='rossant@github',
        packages=['qtools',
                  # 'qtools.qtpy',
                  'qtools.tests',
                  ],
        package_data={
            # 'qtools': [],
        },
        # scripts=[''],
        url='https://github.com/rossant/qtools',
        license='LICENSE.md',
        description='Python tools for Qt.',
        long_description=LONG_DESCRIPTION,
        install_requires=[
        ],
        test_suite = 'nose.collector',
    )
