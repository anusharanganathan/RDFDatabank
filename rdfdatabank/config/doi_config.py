#-*- coding: utf-8 -*-
from pylons import config

class OxDataciteDoi():
    def __init__(self):
        """
            DOI service provided by the British Library on behalf of Datacite.org
            API Doc: https://api.datacite.org/
            Metadata requirements: http://datacite.org/schema/DataCite-MetadataKernel_v2.0.pdf
        """
        #Details pertaining to account with datacite
        self.account = "xx.xxxx"
        self.description = "Oxford University Library Service Databank"
        self.contact = "Name of contact person"
        self.email = "email_goes_here"
        self.password = "xxxxxxx"
        self.domain = "ox.ac.uk"
        self.prefix = "10.5072" #test-prefix
        self.quota = 500000

        if config.has_key("doi.count"):
            self.doi_count_file = config['doi.count']

        #Datacite api endpoint
        #self.endpoint_host = "api.datacite.org"
        self.endpoint_host = "mds.datacite.org"
        self.endpoint_path_doi = "/doi"
        self.endpoint_path_metadata = "/metadata"
