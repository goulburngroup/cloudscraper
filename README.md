cloudscraper
============

Tools to archive usage data and graphs from CloudTrax Dashboard (www.cloudtrax.com)

Installation
============

Dependencies
------------

CloudScraper is written in Python. It is tested and known working on Python 2.7

Modules
- Beautiful Soup - HTML parser
- ConfigObj - Config file reader
- PIL - Python Imaging Library to read and decode images
- Requests - HTTP library
- Texttable - Simple text table formatting library

Debian/Ubuntu
-------------

You should already have Python installed, but you will need to install some modules

> apt-get install python-beautifulsoup python-configobj python-imaging python-pip \
                  python-requests 
> pip install texttable



CloudTrax notes
===============

- The "Last Checkin" item in the nodes status is usually a single item list which contains the time since that node has communicated with CloudTrax. This is reported in Minutes and Hours.
- If a node does not report back to CloudTrax within 26 minutes, the "Last Checkin" field will turn into a two item list where the first item contains the text "Late!" and the second item contains the time since that node has communicated with CloudTrax.
- If a node does not report back to CloudTrax within 33 minutes, "Status" field will change to a "Down" state, but the "Last Checkin" field will continue to show a "Late!" status.
- If a node does not report back to CloudTrax within 60 minutes, the "Last Checkin" field will change to show a "Down!" status.
