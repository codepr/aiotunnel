from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

required = ['aiohttp']

setup(
    name='aiotunnel',
    version='1.2.0',
    description='HTTP tunnel on top of aiohttp and asyncio',
    long_description=readme,
    author='Andrea Giacomo Baldan',
    author_email='a.g.baldan@gmail.com',
    packages=['aiotunnel'],
    install_requires=required,
    scripts=['scripts/aiotunnel']
)
