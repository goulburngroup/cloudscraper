CloudScraper
============

Tools to archive usage data and graphs from CloudTrax Dashboard (www.cloudtrax.com)

Requirements
------------

* Python (Known working with Python 2.7)
* Beautiful Soup - HTML parser
* ConfigObj - Config file reader
* PIL - Python Imaging Library to read and decode images
* pyGal - Python SVG charts creator
* CairoSVG - Convert SVG image to PNG, PDF and PS
* TinyCSS - CSS parser for Python
* CSSselect - CSS selectors for Python
* Requests - HTTP library
* SMTPlib - SMTP library
* Texttable - Simple text table formatting library

Debian/Ubuntu
-------------

You should already have Python installed, but you will need to install some modules

    # apt-get install python-beautifulsoup python-configobj python-imaging
    # apt-get install python-mailer python-pip python-requests 
    # pip install texttable

PostgreSQL
----------

Install PostgreSQL
    # apt-get install postgresql

Log into the database server
    # psql -d template1 -U postgres
    psql (9.1.6, server 9.1.9)
    Type "help" for help.

    template1=#

Create database user
    template1=# CREATE USER scraper WITH PASSWORD 'secretpassword';

Create database
    template1=# CREATE DATABASE cloudscraper;

Grant privileges on database
    template1=# GRANT ALL PRIVILEGES ON DATABASE cloudscraper TO scraper;

* If your database is on a different host to the script, you may need to modify
  pg_hba.conf

CloudTrax notes
===============

- The "Last Checkin" item in the nodes status is usually a single item list which contains the time since that node has communicated with CloudTrax. This is reported in Minutes and Hours.
- If a node does not report back to CloudTrax within 26 minutes, the "Last Checkin" field will turn into a two item list where the first item contains the text "Late!" and the second item contains the time since that node has communicated with CloudTrax.
- If a node does not report back to CloudTrax within 33 minutes, "Status" field will change to a "Down" state, but the "Last Checkin" field will continue to show a "Late!" status.
- If a node does not report back to CloudTrax within 60 minutes, the "Last Checkin" field will change to show a "Down!" status.
