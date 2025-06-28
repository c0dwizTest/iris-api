from setuptools import setup, find_packages

setup(
    name="iris-api",
    version="1.0.0",
    description="A Python package for the iris-api project.",
    author="c0dwizTest",
    author_email="",
    url="https://github.com/c0dwizTest/iris-api",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
