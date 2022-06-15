from setuptools import setup, find_packages

setup(
        name="dk154_kn_targets",
        version="0.1.0",
        #description="Run suite for DXS reduction",
        #url="https://github.com/aidansedgewick/dxs",
        author="aidan-sedgewick",
        author_email='aidansedgewick@gmail.com',
        license="MIT license",
        #install_requires=requirements,
        packages = find_packages(),
)

from dk154_kn_targets.paths import create_all_paths
create_all_paths()

print("are we ready to go?")
