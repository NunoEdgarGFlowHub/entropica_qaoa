#   Copyright 2019 Entropica Labs
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="entropica_qaoa",
    version="1.0",
    description="Entropica Labs QAOA package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Entropica Labs: Jan Lukas Bosse, Ewan Munro",
    author_email="janlukas@entropicalabs.com, ewan@entropicalabs.com",
    url="https://docs.entropicalabs.io/qaoa/",
    packages=find_packages(),
    install_requires=['scipy >= 0.9', 'pyquil >= 2.0',
                      'custom_inherit >= 2.0', 'pandas >= 0.25',
                      'matplotlib >= 3.0']
)
