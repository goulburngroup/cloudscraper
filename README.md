CloudScraper
============

Tools to collect usage data from the CloudTrax API (api.cloudtrax.com)

Requirements
------------

* Python (known working with Python 2.7)
* Requests - HTTP library
* SMTPlib - SMTP library

Debian/Ubuntu
-------------

You should already have Python installed, but you will need to install some modules

    # apt-get install python-mailer python-requests

PostgreSQL
----------

Install PostgreSQL

    # apt-get install postgresql

Log into the database server

    # psql -d template1 -U postgres
    template1=#

Create database user

    template1=# CREATE USER cloudscraper WITH PASSWORD 'secretpassword';

Create database

    template1=# CREATE DATABASE cloudscraper;

Connect to the new database and grant privileges

    template1=# \c cloudscraper
    cloudscraper=# GRANT CONNECT ON DATABASE cloudscraper TO cloudscraper;
    cloudscraper=# GRANT USAGE, CREATE ON SCHEMA public TO cloudscraper;

If your database is on a different host to the script, you may need to modify pg_hba.conf.
In the following example we are allowing the entire 192.168.0.0/255.255.255.0 network to
connect to the 'cloudscraper' database as user 'cloudscraper' using md5 authentication.

    # TYPE  DATABASE        USER            ADDRESS                 METHOD
    host    cloudscraper    cloudscraper    192.168.0.0/24          md5

Setup
-----

Cloudscraper can be run directly from a checkout of the repository.  Just copy
`cloudscraper.conf.example` to the location of your choice, edit it with the
particulars of your configuration, and then run `cloudscraper.py`.  The default
configuration file location is `/opt/cloudscraper/cloudscraper.conf`, but you
may specify a different path with the `--config` option when running the script.
