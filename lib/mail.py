#!/usr/bin/env python
""" lib/email.py

 Email class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import logging
import smtplib

class Email:
    """Email connector class"""

    def __init__(self, config):
        """Constructor"""

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
        """Attach a plain-text alternative"""
        part = MIMEText(text_part)
        self.alternative.attach(part)

    def attach_html(self, html_part):
        """Attach a HTML alternative"""
        part = MIMEText(html_part, 'html')
        self.alternative.attach(part)

    def attach_image(self, image):
        """Attach an image"""
        self.image_count += 1

        part = MIMEImage(image)
        part.add_header('Content-ID', "<image%s>" % self.image_count)

        self.email.attach(part)

    def send(self):
        """Send email"""

        logging.info('Connecting to SMTP server')

        mailer = smtplib.SMTP(self.smtp_server)

        if self.smtp_auth:
            logging.info('Authenticating to SMTP server')
            mailer.login(self.smtp_username,
                         self.smtp_password)

        mailer.sendmail(self.email_from, self.email_to.split(), self.email.as_string())
        mailer.quit()

