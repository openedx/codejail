"""CodeJail: manages execution of untrusted code in secure sandboxes."""

from setuptools import setup

setup(
    name="codejail",
    version="3.0.1",
    packages=['codejail'],
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Ubuntu",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.8',
    ],
)
