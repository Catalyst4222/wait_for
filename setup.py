from setuptools import setup

from interactions.ext.wait_for import __version__

# with open("README.md", "r", encoding="utf-8") as f:
#     long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="interactions-wait-for",
    version=__version__,
    description="Add a wait_for function to discord-py-interactions",
    # long_description=long_description,
    # long_description_content_type="text/markdown",
    url="https://github.com/Catalyst4222/interactions-wait-for",
    author="Catalyst4",
    author_email="catalyst4222@gmail.com",
    license="MIT",
    packages=["interactions.ext.wait_for"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=requirements,
)
