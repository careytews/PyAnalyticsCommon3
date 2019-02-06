import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="PyAnalyticsCommon",
    version="0.0.4",
    author="Trust Networks",
    author_email="support@trustnetworks.com",
    description="Common code for python analytics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="git@github.com:TrustNetworks/PyAnalyticsCommon3.git",
    packages=setuptools.find_packages(),
    install_requires=[
        'pika',
        'prometheus_client'
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ),
)
