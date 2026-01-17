# I hate money

[![GitHub Actions Status](https://github.com/spiral-project/ihatemoney/actions/workflows/test-docs.yml/badge.svg)](https://github.com/spiral-project/ihatemoney/actions/workflows/test-docs.yml)
[![Translation status from Weblate](https://hosted.weblate.org/widgets/i-hate-money/-/i-hate-money/svg-badge.svg)](https://hosted.weblate.org/engage/i-hate-money/?utm_source=widget)
[![Donate](https://img.shields.io/liberapay/receives/IHateMoney.svg?logo=liberapay)](https://liberapay.com/IHateMoney/donate)
[![Docker image](https://img.shields.io/badge/-Docker%20image-black?logo=docker)](https://hub.docker.com/r/ihatemoney/ihatemoney)

*I hate money* is a web application made to ease shared budget
management. It keeps track of who bought what, when, and for whom; and
helps to settle the bills.

-   [Online documentation](https://ihatemoney.readthedocs.io)
-   [Hosted version](https://ihatemoney.org)
-   [Cloud Providers](https://ihatemoney.readthedocs.io/en/latest/installation.html#cloud)
-   [Mailing
    list](https://mailman.alwaysdata.com/postorius/lists/info.ihatemoney.org/)
    (to get updates when needed).

The code is distributed under a BSD *beerware* derivative: if you meet
the people in person and you want to pay them a craft beer, you are
highly encouraged to do so.

## Requirements


-   **Python**: version 3.11 to 3.13.
-   **Backends**: SQLite, PostgreSQL, MariaDB (version 10.3.2 or above),
    Memory.

Usually, we aim to support the software environment of the current Linux Debian
stable and the previous one (old-stable). Docker installation is offered for
broader support.

## Current direction (as of 2024)

Ihatemoney was started in 2011, and we believe the project has reached a certain
level of maturity now. The overall energy of contributors is not as high as it
used to be.

In addition, there are now several self-hosted alternatives (for instance
[cospend](https://github.com/julien-nc/cospend-nc/tree/main),
[spliit](https://github.com/spliit-app/spliit)).

As maintainers, we believe that the project is still relevant but should gear
towards some kind of "maintenance mode":

* **Simplicity** is now the main goal of the project. It has always been a compass
for the project, and the resulting software is appreciated by both users and
server administrators. For us, "simplicity" is positive and encompasses both
technical aspects (very few javascript code, manageable dependencies, small code
size...) and user-visible aspects (straightforward interface, no need to create
accounts for people you invite, same web interface on mobile...)

* **Stability** is prioritized over adding major new features. We found ourselves
complexifying the codebase (and the interface) while accepting some
contributions. Our goal now is to have a minimal set of features that do most of
the job. We believe this will help lower the maintainance burden.

* **User interface and user experience improvements** are always super welcome !

It is still possible to propose new features, but they should fit into
this new direction. Simplicity of the UI/UX and simplicity of the technical
implementation will be the main factors when deciding to accept new features.

## Contributing

Do you wish to contribute to IHateMoney? Fantastic! There's a lot of
very useful help on the official
[contributing](https://ihatemoney.readthedocs.io/en/latest/contributing.html)
page.

You can also [donate some
money](https://liberapay.com/IHateMoney/donate). All funds will be used
to maintain the [hosted version](https://ihatemoney.org).

**Join the other contributors.**

[![](https://contrib.rocks/image?repo=spiral-project/ihatemoney)](https://github.com/spiral-project/ihatemoney/graphs/contributors)
 
## Translation status

[![Translation status for each language](https://hosted.weblate.org/widgets/i-hate-money/-/i-hate-money/multi-blue.svg)](https://hosted.weblate.org/engage/i-hate-money/?utm_source=widget)
