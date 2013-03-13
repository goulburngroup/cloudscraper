#!/usr/bin/env python

from requests import session
from BeautifulSoup import BeautifulSoup
import argparse
import ConfigParser

config_file = 'cloudscraper.conf'

cloudtrax_base = 'https://cloudtrax.com/'
loginurl = 'dashboard.php'
dataurl = 'nodes_attnt2.php'
userurl = 'users2.php'


class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, network):
        self.network = network

        self.config = ConfigParser.RawConfigParser()
        self.config.read(config_file)
        self.username = self.config.get('set_your_network', 'username')
        self.password = self.config.get('set_your_network', 'password')

    def login(self):
        self.session = session()
        s = self.session.post(cloudtrax_base + loginurl, 
                              data={'account': self.username,
                                    'password': self.password,
                                    'status': 'View Status'})

        s.raise_for_status()

        return self.session

    def getSession(self):
        return self.session

    def getRequest(self):
        return self.request

    def getStatus(self):
        self.request = self.session.get(cloudtrax_base + dataurl,
                                        params={'network': self.network,
                                                'showall': '1',
                                                'details': '1'})

        if self.request.status_code == 200:
            distilled_table = BeautifulSoup(self.request.content).find('table', {'id': 'mytable'})

            keys = ('type', 'name', 'comment', 'mac', 'ip', 'chan_24', 'chan_58', 'users_24', 'download_24', 'upload_24', 'uptime', 'fw_version', 'fw_name', 'load', 'memfree', 'time_since_checkin', 'gateway_name', 'gateway_ip', 'hops', 'latency')

            for row in distilled_table.findAll('tr'):
                cell_count = 0
                text_list = []
                values = []

                for cell in row.findAll('td'):
                    text_list = cell.findAll(text=True)

                    for text in text_list:
                        values.append(text)
                        if cell_count == 1 and len(text_list) == 1:
                            values.append('NO COMMENT')
                            
                    cell_count += 1
                print dict(zip(keys, values))
        else:
            print "It's all bad!!!!"

        return self.request
    
       
#
# Program starts here!
#

parser = argparse.ArgumentParser(description='Statistics scraper for the CloudTrax controller')
parser.add_argument('--screen')

cloudtrax = CloudTrax('set_your_network')
cloudtrax.login()
cloudtrax.getStatus()

