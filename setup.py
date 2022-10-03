"""CodeJail: manages execution of untrusted code in secure sandboxes."""
import os
import re

from setuptools import find_packages, setup

with open('README.rst') as readme:
    long_description = readme.read()


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    with open(filename, encoding='utf-8') as opened_file:
        version_file = opened_file.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


VERSION = get_version("codejail", "__init__.py")


setup(
    name="edx-codejail",
    version=VERSION,
    license='Apache',
    description='CodeJail manages execution of untrusted code in secure sandboxes. It is designed primarily for '
                'Python execution, but can be used for other languages as well.',
    long_description=long_description,
    keywords='edx codejail',
    author='edX',
    author_email="oscm@edx.org",
    url='https://github.com/openedx/codejail',
    scripts=['proxy_main.py', 'memory_stress.py'],
    packages=find_packages(
        include=['codejail', 'codejail.*'],
        exclude=["*tests"],
    ),
    include_package_data=True,
    install_requires=['six'],
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
)
