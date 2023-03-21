"""Web server Tableau uses to run Python scripts.

TabPy (the Tableau Python Server) is an external service implementation
which expands Tableau's capabilities by allowing users to execute Python
scripts and saved functions via Tableau's table calculations.
"""

import os
from setuptools import setup, find_packages
import unittest


DOCLINES = (__doc__ or "").split("\n")


def setup_package():
    def read(fname):
        return open(os.path.join(os.path.dirname(__file__), fname)).read()

    setup(
        name="tabpy",
        version=read("tabpy/VERSION"),
        description=DOCLINES[0],
        long_description="\n".join(DOCLINES[1:]) + "\n" + read("CHANGELOG"),
        long_description_content_type="text/markdown",
        url="https://github.com/tableau/TabPy",
        author="Tableau",
        author_email="github@tableau.com",
        maintainer="Tableau",
        maintainer_email="github@tableau.com",
        download_url="https://pypi.org/project/tabpy",
        project_urls={
            "Bug Tracker": "https://github.com/tableau/TabPy/issues",
            "Documentation": "https://tableau.github.io/TabPy/",
            "Source Code": "https://github.com/tableau/TabPy",
        },
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Topic :: Scientific/Engineering",
            "Topic :: Scientific/Engineering :: Information Analysis",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: POSIX",
            "Operating System :: Unix",
            "Operating System :: MacOS",
        ],
        platforms=["Windows", "Linux", "Mac OS-X", "Unix"],
        keywords=["tabpy tableau"],
        packages=find_packages(exclude=["docs", "misc"]),
        package_data={
            "tabpy": [
                "VERSION",
                "tabpy_server/state.ini.template",
                "tabpy_server/static/*",
                "tabpy_server/common/default.conf",
            ]
        },
        python_requires=">=3.7",
        license="MIT",
        # Note: many of these required packages are included in base python
        # but are listed here because different linux distros use custom
        # python installations.  And users can remove packages at any point
        install_requires=[
            "cloudpickle",
            "configparser",
            "coverage",
            "coveralls",
            "docopt",
            "future",
            "genson",
            "hypothesis",
            "jsonschema",
            "mock",
            "nltk",
            "numpy",
            "pandas",
            "pyopenssl",
            "pytest",
            "pytest-cov",
            "requests",
            "scipy",
            "simplejson",
            "scikit-learn",
            "textblob",
            "tornado",
            "twisted",
            "urllib3",
        ],
        entry_points={
            "console_scripts": [
                "tabpy=tabpy.tabpy:main",
                "tabpy-deploy-models=tabpy.models.deploy_models:main",
                "tabpy-user=tabpy.utils.tabpy_user:main",
            ],
        },
        setup_requires=["pytest-runner"],
        test_suite="pytest",
    )


if __name__ == "__main__":
    setup_package()
