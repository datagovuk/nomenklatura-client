from setuptools import setup, find_packages

setup(
    name='nkclient',
    version='0.1',
    description="Client library for nomenklatura, make record linkages on the web.",
    long_description='',
    classifiers=[
        ],
    keywords='data mapping identity linkage record',
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    url='http://okfn.org',
    license='AGPLv3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=[],
    include_package_data=False,
    zip_safe=False,
    install_requires=[
        "requests>=1.1"
    ],
    tests_require=[],
    entry_points=\
    """ """,
)
