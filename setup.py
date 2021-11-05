import pathlib
import re
from setuptools import setup

HERE = pathlib.Path(__file__).parent

# Get long_description value
README = (HERE/'README.md').read_text()

#Extract version value from __init__.py
version_regex = r'__version__ = ["\'](.+)["\']'
text = (HERE/"withings/__init__.py").read_text()
VERSION = re.search(version_regex, text).group(1)

setup(
    name="python-withings",
    version="1.0.0",
    description="Wrapper package for Withings API",
    long_description_content_type="text/markdown",
    long_description=README,
    url="https://github.com/strohganoff/python-withings",
    packages=["withings", "withings/oauth2"],
    include_package_data=True,
    install_requires=["requests-oauthlib","python-dateutil"],
)