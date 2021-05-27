# To make distribution
# run setup tools build_py
# Zip output directory and overwrite zip in latest and add version
# Update Help, make pdf with: https://www.markdowntopdf.com/

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='DXFImporter',
    version='1.0.9',
    description='A utility for Fusion 360 to import multiple DXF files.',
    long_description=long_description,
    packages=['DXFImporter', 'DXFImporter.apper.apper', 'DXFImporter.commands', 'DXFImporter.lib.ezdxf'],
    package_data={
        "": ["resources/*", "resources/**/*", "*.manifest", "LICENSE", "HelpFile.pdf", "HelpFile.html",
             "default_preferences.json"],
    },
    url='https://github.com/tapnair/DXFImporter',
    license='MIT',
    author='Patrick Rainsberry',
    author_email='patrick.rainsberry@autodesk.com',
)
