from setuptools import setup, find_packages
from os import path


def setup_package():
    here = path.abspath(path.dirname(__file__))

    with open(path.join(here, 'VERSION'), encoding='utf-8') as f:
        version = f.read()

    setup(
        name='tabpy',
        version=version,
        description='Web server Tableau uses to run Python scripts.',
        long_description=(
            'TabPy (Tableau Python Server) is external server '
            'implementation which allows expanding Tableau with '
            'executing Python scripts in table calculation.'),
        long_description_content_type='text/markdown',
        url='https://github.com/tableau/TabPy',
        author='Tableau',
        author_email='github@tableau.com',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.6',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: Information Analysis',
        ],
        keywords=['tabpy tableau'],
        packages=find_packages(
            exclude=['docs', 'misc', 'tests']),
        python_requires='>=3.6',
        license='MIT',
        # Note: many of these required packages are included in base python
        # but are listed here because different linux distros use custom
        # python installations.  And users can remove packages at any point
        install_requires=[
            'backports_abc',
            'cloudpickle',
            'configparser',
            'decorator',
            'future',
            'genson',
            'mock',
            'numpy',
            'pyopenssl',
            'python-dateutil',
            'requests',
            'singledispatch',
            'six',
            'tornado',
            'urllib3<1.25,>=1.21.1'
        ],
        entry_points={
            'console_scripts': [
                'tabpy=tabpy.tabpy:main',
            ],
        }
    )


if __name__ == '__main__':
    setup_package()
