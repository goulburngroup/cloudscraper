#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
"""lib/mail.py

Email convenience module for cloudscraper reporting.

This module provides a convenience wrapper for sending multi-part email
messages according to settings in the cloudscraper configuration.

© 2016 The Goulburn Group http://www.goulburngroup.com.au, all rights reserved.

Authors:
    Alex Ferrara <alex@receptiveit.com.au>
    Brendan Jurd <direvus@gmail.com>
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import logging
import smtplib


class Email:
    def __init__(self, config):
        self.email_from = config['from']
        self.email_to = config['to']
        self.email_subject = config['subject']

        self.smtp_server = config['server']

        if 'username' in config.keys():
            self.smtp_auth = True
            self.smtp_username = config['username']
            self.smtp_password = config['password']
        else:
            self.smtp_auth = False

        self.email = MIMEMultipart('related')
        self.email['Subject'] = self.email_subject
        self.email['From'] = self.email_from
        self.email['To'] = self.email_to
        self.email.preamble = 'This is a multi-part message in MIME format.'

        self.image_count = 0

        # Encapsulate the plain and HTML versions of the message body
        # in an 'alternative' part, so message agents can decide which
        # they want to display.

        self.alternative = MIMEMultipart('alternative')
        self.email.attach(self.alternative)

    def attach_text(self, text_part):
        """Attach a plain-text alternative part."""
        part = MIMEText(text_part)
        self.alternative.attach(part)

    def attach_html(self, html_part):
        """Attach a HTML alternative part."""
        part = MIMEText(html_part, 'html')
        self.alternative.attach(part)

    def attach_image(self, image):
        """Add an image attachment."""
        self.image_count += 1

        part = MIMEImage(image)
        part.add_header('Content-ID', "<image%s>" % self.image_count)

        self.email.attach(part)

    def send(self):
        logging.info('Connecting to SMTP server')
        mailer = smtplib.SMTP(self.smtp_server)

        if self.smtp_auth:
            logging.info('Authenticating to SMTP server')
            mailer.login(self.smtp_username,
                         self.smtp_password)

        mailer.sendmail(self.email_from, self.email_to.split(), self.email.as_string())
        mailer.quit()
