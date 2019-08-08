import os
from setuptools import setup, find_packages


def setup_package():
    def read(fname):
        return open(os.path.join(os.path.dirname(__file__), fname)).read()

    setup(
        name='tabpy',
        version=read('VERSION'),
        description='Web server Tableau uses to run Python scripts.',
        long_description=read('README.md'),
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
        package_data={
            'tabpy': [
                'VERSION',
                'tabpy_server/state.ini',
                'tabpy_server/common/default.conf'
            ]
        },
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
            'jsonschema',
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
                'tabpy-deploy-models=tabpy.models.deploy_models:main'
            ],
        }
    )


if __name__ == '__main__':
    setup_package()
