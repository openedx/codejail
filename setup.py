"""
CodeJail: manages execution of untrusted code in secure sandboxes.
"""

from setuptools import setup

setup(
    name="codejail",
    version="1.0",
    packages=['codejail'],
    description="Manages execution of untrusted code in secure sandboxes.",
    license="Apache Software License, version 2.0",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Ubuntu",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7",
    ],
)
