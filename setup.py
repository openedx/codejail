"""CodeJail: manages execution of untrusted code in secure sandboxes."""

from setuptools import setup

with open('README.rst') as readme:
    long_description = readme.read()

setup(
    name="codejail",
    version="3.1.4",
    license='Apache',
    description='CodeJail manages execution of untrusted code in secure sandboxes. It is designed primarily for '
                'Python execution, but can be used for other languages as well.',
    long_description=long_description,
    keywords='edx codejail',
    author='edX',
    author_email="oscm@edx.org",
    url='https://github.com/edx/codejail',
    packages=['codejail'],
    install_requires=['six'],
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.8',
    ],
)
