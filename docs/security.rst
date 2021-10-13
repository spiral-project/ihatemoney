Security
########

Ihatemoney does not have user accounts. Instead, authorization is based around
shared projects: this is a bit unusual and deserves some explanation about
the security model.

First of all, Ihatemoney fundamentally assumes that all members of a project trust
each other. Otherwise, you would probably not share expenses in the first place!

That being said, there are a few mechanisms to limit the impact of a malicious
member and to manage changes in membership (e.g. ensuring that a previous member
can no longer access the project). But these mechanisms don't prevent a malicious member
from breaking things in your project!

Security model
==============

A project has three main parameters when it comes to security:

- **project identifier** (equivalent to a "login")
- **private code** (equivalent to a "password")
- **token** (cryptographically derived from the private code)

Somebody with the private code can:

- access the project through the web interface or the API
- add, modify or remove bills
- view project history
- change basic settings of the project
- change the email address associated to the project
- change the private code of the project

Somebody with the token can manipulate the project through the API to
do essentially the same thing:

- access the project
- add, modify or remove bills
- change basic settings of the project
- change the email address associated to the project
- change the private code of the project

The token can also be used to build "invitation links". These links allow
to login on the web interface without knowing the private code, see below.

Giving access to a project
==========================

There are two main ways to give access to a project to a new person:

- share the project identifier and private code using any out-of-band
  communication method

- share an invitation link that allows to login on the web interface
  without knowing the private code

The second method is interesting because it does not reveal the private code.
In particular, somebody that is logged-in through the invitation link will not be able
to change the private code, because the web interface requires a confirmation
of the existing private code to change it.
However, a motivated person could extract the token from the invitation link,
use it to access the project through the API, and change the private code through
the API.

Removing access to a project
============================

If a person should no longer be able to access a project, the only way is to change
the private code.

This will also automatically change the token: old invitation links won't
work anymore, and anybody with the old token will no longer be able to access
the project through the API.

Recovering access to a project
==============================

If the private code is no longer known, the creator of the project can still recover
access. He/she must have provided an email address when creating the project,
and Ihatemoney can send a reset link to this email address (classical "forgot
your password" functionality).

Note, however, that somebody with the private code could have changed the email
address in the settings at any time.

Recovering lost data
====================

A member can delete or change bills. There is no way to revert such actions for now.
However, each project has an history page that lists all actions done on the project.
This history can be used to manually correct previous changes.

Note, however, that the history feature is primarily meant to protect against mistakes:
a malicious member can easily remove all entries from the history!

The best defense against this kind of issues is... backups! All data for a project can be
exported through the settings page or through the API.
