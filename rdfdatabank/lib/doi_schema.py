#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2012 University of Oxford

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, --INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from rdfdatabank.config.namespaces import NAMESPACES

class DataciteDoiSchema():
    def __init__(self, doi):
        """
            DOI service provided by the British Library on behalf of Datacite.org
            API Doc: https://api.datacite.org/
            Metadata requirements: http://datacite.org/schema/DataCite-MetadataKernel_v2.0.pdf
        """
        self.doi = doi

        #Mandatory metadata
        self.mandatory_metadata={
            #'doi':[NAMESPACES['bibo']['doi']],
            'creator':[
                NAMESPACES['dc']['creator'], 
                NAMESPACES['dcterms']['creator']
            ],
            'title':[
                NAMESPACES['dc']['title'], 
                NAMESPACES['dcterms']['title']
            ],
            'publisher':[
                NAMESPACES['dc']['publisher'], 
                NAMESPACES['dcterms']['publisher']
            ],
            'publicationYear':[
                NAMESPACES['oxds']['embargoedUntil'], 
                NAMESPACES['dcterms']['issued'], 
                NAMESPACES['dcterms']['modified'], 
                NAMESPACES['dcterms']['date'],
                NAMESPACES['dc']['date']
            ]
        }
         
        self.optional_metadata={
            'subject':[
                NAMESPACES['dc']['subject'], 
                NAMESPACES['dcterms']['subject']
            ],
            'dateAccepted':[
                NAMESPACES['dcterms']['dateAccepted']
            ],
            'embargoedUntil':[
                NAMESPACES['oxds']['embargoedUntil']
            ],
            'dateCopyrighted':[
                NAMESPACES['dcterms']['dateCopyrighted']
            ],
            'created':[
                NAMESPACES['dcterms']['created']
            ],
            'issued':[
                NAMESPACES['dcterms']['issued']
            ],
            'dateSubmitted':[
                NAMESPACES['dcterms']['dateSubmitted']
            ],
            'modified':[
                NAMESPACES['dcterms']['modified']
            ],
            'date':[
                NAMESPACES['dcterms']['date'],
                NAMESPACES['dc']['date']
            ],
            'language':[
                NAMESPACES['dc']['language'],
                NAMESPACES['dcterms']['language']
            ],
            'identifier':[
                NAMESPACES['dc']['identifier'], 
                NAMESPACES['dcterms']['identifier']
            ],
            'uri':[
                NAMESPACES['dc']['identifier'], 
                NAMESPACES['dcterms']['identifier'], 
                NAMESPACES['bibo']['uri']
            ],
            'asin':[
                NAMESPACES['bibo']['asin']
            ],
            'coden':[
                NAMESPACES['bibo']['coden']
            ],
            'eanucc13':[
                NAMESPACES['bibo']['eanucc13']
            ],
            'eissn':[
                NAMESPACES['bibo']['eissn']
            ],
            'gtin14':[
                NAMESPACES['bibo']['gtin14']
            ],
            'handle':[
                NAMESPACES['bibo']['handle']
            ],
            'isbn':[
                NAMESPACES['bibo']['isbn']
            ],
            'isbn10':[
                NAMESPACES['bibo']['sbn10']
            ],
            'isbn13':[
                NAMESPACES['bibo']['isbn13']
            ],
            'issn':[
                NAMESPACES['bibo']['issn']
            ],
            'lccn':[
                NAMESPACES['bibo']['lccn']
            ],
            'oclcnum':[
                NAMESPACES['bibo']['oclcnum']
            ],
            'pmid':[
                NAMESPACES['bibo']['pmid']
            ],
            'sici':[
                NAMESPACES['bibo']['sici']
            ],
            'upc':[
                NAMESPACES['bibo']['upc']
            ],
            'size':[
                NAMESPACES['dcterms']['extent']
            ],
            'format':[
                NAMESPACES['dc']['format'],
                NAMESPACES['dcterms']['format']
            ],
            'version':[
                NAMESPACES['oxds']['currentVersion']
            ],
            'rights':[
                NAMESPACES['dc']['rights'],
                NAMESPACES['dcterms']['rights']
            ],
            'description':[
                NAMESPACES['dc']['description'],
                NAMESPACES['dcterms']['description']
            ],
            'abstract':[
                NAMESPACES['dcterms']['abstract']
            ]
            #'RelatedIdentifier':[]],
            #'contributor':[
            #    NAMESPACES['dc']['contributor'],
            #    NAMESPACES['dcterms']['contributor']
            #],
            #'resourceType':[
            #    NAMESPACES['dc']['type',
            #    NAMESPACES['dcterms']['type']
            #],
        }

        self.multiValued = ['creator', 'subject', 'size', 'format']
        self.empty_tags = ['subjects', 'dates', 'alternateIdentifiers', 'sizes', 'formats', 'descriptions']       
 
        self.xml_schema=u"""<resource xmlns="http://datacite.org/schema/kernel-2.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-2.2 http://schema.datacite.org/meta/kernel-2.2/metadata.xsd">
<identifier identifierType="DOI">%s</identifier>
<creators>
<creator><creatorName>${creator}</creatorName></creator>
</creators>
<titles>
<title>${title}</title>
</titles>
<publisher>${publisher}</publisher>
<publicationYear>${publicationYear}</publicationYear>
<subjects>
<subject>${subject}</subject>
</subjects>
<dates>
<date dateType="Accepted">${dateAccepted}</date>
<date dateType="Available">${embargoedUntil}</date>
<date dateType="Copyrighted">${dateCopyrighted}</date>
<date dateType="Created">${created}</date>
<date dateType="Issued">${issued}</date>
<date dateType="Submitted">${dateSubmitted}</date>
<date dateType="Updated">${modified}</date>
<date dateType="Valid">${date}</date>
</dates>
<language>${language}</language>
<resourceType resourceTypeGeneral="Dataset">Dataset</resourceType>
<alternateIdentifiers>
<alternateIdentifier alternateIdentifierType="Source identifier">${identifier}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="uri">${uri}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="asin">${asin}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="coden">${coden}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="eanucc13">${eanucc13}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="eISSN">${eissn}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="gtin14">${gtin14}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="handle">${handle}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="isbn">${isbn}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="isbn">${isbn10}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="isbn">${isbn13}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="issn">${issn}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="lccn">${lccn}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="oclcnum">${oclcnum}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="pmid">${pmid}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="sici">${sici}</alternateIdentifier>
<alternateIdentifier alternateIdentifierType="upc">${upc}</alternateIdentifier>
</alternateIdentifiers>
<sizes>
<size>${size}</size>
</sizes>
<formats>
<format>${format}</format>
</formats>
<version>${version}</version>
<rights>${rights}</rights>
<descriptions>
<description descriptionType="Other">${description}</description>
<description descriptionType="Abstract">${abstract}</description>
</descriptions>
</resource>
"""%doi
