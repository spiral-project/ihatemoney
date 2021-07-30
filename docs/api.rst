The REST API
############

All of what's possible to do with the website is also possible via a web API.
This document explains how the API is organized and how you can query it.

The only supported data format is JSON.

Overall organisation
====================

You can access three different things: projects, members and bills. You can
also get the balance for a project.

The examples here are using curl, feel free to use whatever you want to do the
same thing, curl is not a requirement.

Authentication
--------------

To interact with bills and members, and for any action other than creating a new
project, you need to be authenticated. The simplest way to authenticate is to use
"basic" HTTP authentication with the project ID and private code.

For instance, to obtain information about a project, using curl::

    $ curl --basic -u demo:demo https://ihatemoney.org/api/projects/demo

It is also possible to generate a token, and then use it later to authenticate
instead of basic auth.
For instance, start by generating the token (of course, you need to authenticate)::

    $ curl --basic -u demo:demo https://ihatemoney.org/api/projects/demo/token
    {"token": "eyJwcm9qZWN0X2lkIjoiZGVtbyJ9.M86C3AiZa_SFEyiddYXdTh2-OOI"}

Make sure to store this token securely: it allows full access to the project.
For instance, use it to obtain information about the project (replace PROJECT_TOKEN with
the actual token)::

    $ curl --oauth2-bearer "PROJECT_TOKEN" https://ihatemoney.org/api/projects/demo

This works by sending the token in the Authorization header, so doing it "manually" with curl
looks like::

    $ curl --header "Authorization: Bearer PROJECT_TOKEN" https://ihatemoney.org/api/projects/demo

This token can also be used to authenticate for a project on the web interface, which can be useful
to generate invitation links. You would simply create an URL of the form::

    https://ihatemoney.org/authenticate?token=PROJECT_TOKEN

Such a link grants full access to the project associated with the token.

Projects
--------

You can't list projects, for security reasons. But you can create, update and
delete one directly from the API.

The URLs are ``/api/projects`` and ``/api/projects/<identifier>``.

Creating a project
~~~~~~~~~~~~~~~~~~

A project needs the following arguments:

* ``name``: The project name (string)
* ``id``: the project identifier (string without special chars or spaces)
* ``password``: the project password / secret code (string)
* ``contact_email``: the contact email

::

    $ curl -X POST https://ihatemoney.org/api/projects \
    -d 'name=yay&id=yay&password=yay&contact_email=yay@notmyidea.org'
    "yay"

As you can see, the API returns the identifier of the project

Getting information about the project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Getting information about the project::


    $ curl --basic -u demo:demo https://ihatemoney.org/api/projects/demo
    {
        "id": "demo",
        "name": "demonstration",
        "contact_email": "demo@notmyidea.org",
        "members": [{"id": 11515, "name": "f", "weight": 1.0, "activated": true, "balance": 0}, 
                    {"id": 11531, "name": "g", "weight": 1.0, "activated": true, "balance": 0}, 
                    {"id": 11532, "name": "peter", "weight": 1.0, "activated": true, "balance": 5.0},
                    {"id": 11558, "name": "Monkey", "weight": 1.0, "activated": true, "balance": 0}, 
                    {"id": 11559, "name": "GG", "weight": 1.0, "activated": true, "balance": -5.0}]
    }


Updating a project
~~~~~~~~~~~~~~~~~~

Updating a project is done with the ``PUT`` verb::

    $ curl --basic -u yay:yay -X PUT\
    https://ihatemoney.org/api/projects/yay -d\
    'name=yay&id=yay&password=yay&contact_email=youpi@notmyidea.org'

Deleting a project
~~~~~~~~~~~~~~~~~~

Just send a DELETE request ont the project URI ::

    $ curl --basic -u demo:demo -X DELETE https://ihatemoney.org/api/projects/demo

Members
-------

You can get all the members with a ``GET`` on ``/api/projects/<id>/members``::

    $ curl --basic -u demo:demo https://ihatemoney.org/api/projects/demo/members\
    [{"weight": 1, "activated": true, "id": 31, "name": "Arnaud"},
     {"weight": 1, "activated": true, "id": 32, "name": "Alexis"},
     {"weight": 1, "activated": true, "id": 33, "name": "Olivier"},
     {"weight": 1, "activated": true, "id": 34, "name": "Fred"}]

Add a member with a ``POST`` request on ``/api/projects/<id>/members``::

    $ curl --basic -u demo:demo -X POST\
    https://ihatemoney.org/api/projects/demo/members -d 'name=tatayoyo'
    35

You can also ``PUT`` a new version of a member (changing its name)::

    $ curl --basic -u demo:demo -X PUT\
    https://ihatemoney.org/api/projects/demo/members/36\
    -d 'name=yeaaaaah'
    {"activated": true, "id": 36, "name": "yeaaaaah", "weight": 1}

Delete a member with a ``DELETE`` request on
``/api/projects/<id>/members/<member-id>``::

    $ curl --basic -u demo:demo -X DELETE\
    https://ihatemoney.org/api/projects/demo/members/35
    "OK

Bills
-----

You can get the list of bills by doing a ``GET`` on
``/api/projects/<id>/bills`` ::

    $ curl --basic -u demo:demo https://ihatemoney.org/api/projects/demo/bills

Add a bill with a ``POST`` query on ``/api/projects/<id>/bills``. you need the
following params:

* ``date``: the date of the bill; defaults to current date if not
  provided. (format is ``yyyy-mm-dd``)
* ``what``: what have been payed
* ``payer``: by who ? (id)
* ``payed_for``: for who ? (id, to set multiple id use a list,
  e.g. ``["id1", "id2"]``)
* ``amount``: amount payed

Returns the id of the created bill ::

    $ curl --basic -u demo:demo -X POST\
    https://ihatemoney.org/api/projects/demo/bills\
    -d "date=2011-09-10&what=raclette&payer=31&payed_for=31&amount=200"
    80

You can also ``PUT`` a new version of the bill at
``/api/projects/<id>/bills/<bill-id>``::

    $ curl --basic -u demo:demo -X PUT\
    https://ihatemoney.org/api/projects/demo/bills/80\
    -d "date=2011-09-10&what=raclette&payer=31&payed_for=31&amount=250"
    80

And you can of course ``DELETE`` them at
``/api/projects/<id>/bills/<bill-id>``::

    $ curl --basic -u demo:demo -X DELETE\
    https://ihatemoney.org/api/projects/demo/bills/80\
    "OK"


Statistics
----------

You can get some project stats with a ``GET`` on
``/api/projects/<id>/statistics``::

    $ curl --basic -u demo:demo https://ihatemoney.org/api/projects/demo/statistics
    [
        {
            "balance": 12.5,
            "member": {"activated": True, "id": 1, "name": "alexis", "weight": 1.0},
            "paid": 25.0,
            "spent": 12.5
        },
        {
            "balance": -12.5,
            "member": {"activated": True, "id": 2, "name": "fred", "weight": 1.0},
            "paid": 0,
            "spent": 12.5
        }
    ]
