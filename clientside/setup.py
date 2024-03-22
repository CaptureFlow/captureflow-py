from setuptools import setup, find_packages

setup(
    name='captureflow',
    version='0.1.0',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    # Add more metadata as needed
)