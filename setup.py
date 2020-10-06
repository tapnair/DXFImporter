from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='DXFImporter',
    version='1.0.4',
    description='A utility for Fusion 360 to import multiple DXF files.',
    long_description=long_description,
    packages=['DXFImporter', 'DXFImporter.apper.apper', 'DXFImporter.commands'],
    package_data={
        "": ["resources/*", "resources/**/*", "*.manifest", "LICENSE"],
    },
    url='https://github.com/tapnair/DXFImporter',
    license='MIT',
    author='Patrick Rainsberry',
    author_email='patrick.rainsberry@autodesk.com',
)
