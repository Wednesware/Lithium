from setuptools import setup, find_packages
               
from lithium import VERSION

                           
setup(
    name="wwli",
    version=VERSION,
    py_modules=[],
    entry_points={
        "console_scripts": [
            "pko=lithium:main",
            "perkeo=lithium:main",
            "lithium=lithium:main",
        ],
    },
    author="Wednesware",
    author_email="team@wednesware.org",
    description="Official compiler for the Perkeo programming language.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://wednesware.org/lithium",
    install_requires=[],
    packages=find_packages(),
    package_data={
        "lithium": [
            "settings.pyon",
            "resources/libpkis/*.pkis",
        ]
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    license="MIT"
)