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

from rdfdatabank.lib.doi_schema import DataciteDoiSchema
from rdfdatabank.config.namespaces import NAMESPACES
from rdflib import URIRef, Literal, BNode
from pylons import app_globals as ag
from dateutil.parser import parse
from time import strftime
import os, codecs, uuid, re

def get_values(key, predicates, item):
    values = []
    answers = []
    # Get answers from all the predicates
    for p in predicates:
        ans = item.list_rdf_objects(item.uri, p)
        if ans:
            answers.extend(ans)
    if not answers:
        if key == "creator":
            return ["First World War Poetry Digital Archive, University of Oxford"]
        return values
    # Clean up the answers
    if key == 'publicationYear':
        for ans in answers:
            if type(ans).__name__ in ['str', 'unicdoe', 'Literal']:
                try:
                    dt_obj = parse(str(ans), dayfirst=True, yearfirst=False)
                    values.append(dt_obj.year)
                except:
                    continue
            else: 
                continue
    elif 'date' in key:
        for ans in answers:
            if type(ans).__name__ in ['str', 'unicdoe', 'Literal']:
                try:
                    dt_obj = parse(ans, dayfirst=True, yearfirst=False)
                    dt_formatted = dt_obj.strftime("%Y-%m-%d")
                    values.append(dt_formatted)
                except:
                    continue
            else:
                continue
    elif key in ['creator', 'contributor', 'publisher']:
        for ans in answers:
            if type(ans).__name__ in ['str', 'unicdoe', 'Literal']:
                ans = ans.strip()
                if ans:
                    values.append(ans)
            elif type(ans).__name__ == 'BNode':
                fn = item.list_rdf_objects(ans, NAMESPACES['foaf']['familyName'])
                ln = item.list_rdf_objects(ans, NAMESPACES['foaf']['givenName'])
                nm = item.list_rdf_objects(ans, NAMESPACES['foaf']['name'])
                if fn and fn[0] and ln and ln[0] and type(fn[0]).__name__ in ['str', 'unicdoe', 'Literal'] and \
                    type(ln[0]).__name__ in ['str', 'unicdoe', 'Literal']:
                    values.append(u"%s,%s"%(ln[0],fn[0]))
                elif nm and nm[0] and type(nm[0]).__name__ in ['str', 'unicdoe', 'Literal']:
                    values.append(nm[0])
        if key == "creator" and not values:
            values.append("First World War Poetry Digital Archive, University of Oxford")
    elif key in ['identifier']:
        for ans in answers:
            if type(ans).__name__ in ['str', 'unicdoe', 'Literal']:
                ans = ans.strip()
                if ans:
                    values.append(ans)
    elif key in ['uri']:
        for ans in answers:
            if type(ans).__name__ == 'URIRef' or ans.startswith('http'):
                values.append(ans)
    else:
        for ans in answers:
            if type(ans).__name__ in ['str', 'unicdoe', 'Literal']:
                ans = ans.strip()
            values.append(ans)
    return values

def get_doi_metadata(doi, item):
    schema = DataciteDoiSchema(doi)
    xml_metadata = []
    values = {}
    #Get values for mandatory fields
    for key, predicates in schema.mandatory_metadata.iteritems():
        answers = get_values(key, predicates, item)
        if not answers:
            return False
        values[key] = answers
    #Get values for optional fields
    for key, predicates in schema.optional_metadata.iteritems():
        answers = get_values(key, predicates, item)
        if answers:
            values[key] = answers
    p = "[$][{](.*?)[}]"
    #construct the xml document based on the template xml_schema
    lines = schema.xml_schema.split('\n')
    for line in lines:
        terms = re.findall(p, line)
        if terms:
            if terms[0] in values:
                if not type(values[terms[0]]).__name__ == 'list':
                    values[terms[0]] = [values[terms[0]]]
                if terms[0] in schema.multiValued:
                    for val in values[terms[0]]:
                        if type(val) == str:
                            val = unicode(val).encode('utf-8')
                        elif not isinstance(val, basestring):
                            val = unicode(val)
                        xml_metadata.append(line.replace("${%s}"%terms[0], val))
                else:
                    val = values[terms[0]][0]
                    if type(val) == str:
                        val = unicode(val).encode('utf-8')
                    elif not isinstance(val, basestring):
                        val = unicode(val)
                    xml_metadata.append(line.replace("${%s}"%terms[0], val))
        else:
            xml_metadata.append(line)
    #Remove empty tags from the xml document
    for tag in schema.empty_tags:
        try:
            start = xml_metadata.index('<%s>'%tag)
            end = xml_metadata.index('</%s>'%tag)
            if start + 1 == end:
                xml_metadata.remove('<%s>'%tag)
                xml_metadata.remove('</%s>'%tag)
        except ValueError:
            continue
    #Convert to string
    xml_metadata = u"\n".join(xml_metadata)
    return xml_metadata

def doi_count(increase=True):
    if not os.path.isfile(ag.doi_count_file):
        count = 0
        if increase:
            count += 1
        f = open(ag.doi_count_file, 'w')
        f.write(str(count))
        f.close()
        return count

    f = open(ag.doi_count_file, 'r')
    count = f.read()
    f.close()
    count = count.replace('\n', '').strip()
    try:
        count = int(count)
    except:
        return False
    if not increase:
        return str(count)

    count += 1
    f = open(ag.doi_count_file, 'w')
    f.write(str(count))
    f.close()
    return count
