# PyAnalyticsCommon
Common code for python analytics used in the analytics cloud.
Such as Subscribers and Publishers

## Build
GoCD will build it for you, local testing can be done by pip installing with edittable mode (-e) locally.

if you have made changes that you think warrant a new 'release' bump the release version in `setup.py`. (this will only affect if someone tries to upgrade an install, so shouldnt affect new docker image builds)


## Install
`pip install git+ssh://git@github.com/TrustNetworks/PyAnalyticsCommon3@master`
