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

from redisqueue import RedisQueue
from LogConfigParser import Config
from solrFields import solr_fields_mapping

import sys
import codecs
from time import sleep
from datetime import datetime, timedelta
from rdflib import URIRef
import simplejson
from collections import defaultdict
from uuid import uuid4

#from recordsilo import Granary
from databankClientLib.databank import Databank
from rdflib import ConjunctiveGraph
from StringIO import StringIO
from solr import SolrConnection

import logging

logger = logging.getLogger("redisqueue")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

class NoSuchSilo(Exception):
  pass

def gather_document(silo_name, item_id, graph, item, debug=False):
    document = defaultdict(list)
    if 'metadata' in item and item['metadata'] and 'uuid' in item['metadata'] and item['metadata']['uuid']:
        document['uuid'].append(item['metadata']['uuid'])
    else:
        document['uuid'].append(item_id)
    document['id'].append(item_id)
    document['silo'].append(silo_name)
    for (_,p,o) in graph.triples((None, None, None)):
        if str(p) in solr_fields_mapping:
            field = solr_fields_mapping[str(p)]
            if field == "aggregatedResource":
                if '/datasets/' in o:
                    fn = unicode(o).split('/datasets/')
                    if len(fn) == 2 and fn[1]:
                        document['filename'].append(unicode(fn[1]).encode("utf-8"))
            if field == "embargoedUntilDate":
                ans = u"%sZ"%unicode(o).split('.')[0]
                document[field].append(unicode(ans).encode("utf-8"))
            else:
                document[field].append(unicode(o).encode("utf-8"))
        else:
            document['text'].append(unicode(o).encode("utf-8"))
    document = dict(document)
    if 'publisher' in document:
        #TODO: SOLR not accepting multiple values for publisher though multivalued fields. Fix this
        del document['publisher']
    if debug:
        f = codecs.open('/var/log/databank/solr_doc.log', 'w', 'utf-8')
        f.write(simplejson.dumps(document))
        f.close()
    return document

if __name__ == "__main__":
    c = Config()
    redis_section = "redis"
    worker_section = "worker_solr"
    worker_number = sys.argv[1]
    hours_before_commit = 1
    if len(sys.argv) == 3:
        if "redis_%s" % sys.argv[2] in c.sections():
            redis_section = "redis_%s" % sys.argv[2]

    rq = RedisQueue(c.get(worker_section, "listento"), "solr_%s" % worker_number,
                  db=c.get(redis_section, "db"), 
                  host=c.get(redis_section, "host"), 
                  port=c.get(redis_section, "port"),
                  errorqueue=c.get(worker_section, "errorq")
                 )

    host = "databank.ora.ox.ac.uk"
    username = "username"
    password = "password"
    db = Databank( host, username, password )

    solr = SolrConnection(c.get(worker_section, "solrurl"))

    idletime = 0.1
    commit_time = datetime.now() + timedelta(hours=hours_before_commit)
    toCommit = False
    tries = 0
    silos = []
    while tries < 5:
        response = db.getSilos()
        if db.good( response ) :
            silos = response.results
            break
        else:
            tries += 1
    while(True):
        sleep(idletime)

        if datetime.now() > commit_time and toCommit:
            solr.commit()
            commit_time = datetime.now() + timedelta(hours=hours_before_commit)
            toCommit = False

        line = rq.pop()

        if not line:
            if toCommit:
                solr.commit()
                toCommit = False
                commit_time = datetime.now() + timedelta(hours=hours_before_commit)
            continue

        logger.debug("Got message %s" %str(line))

        toCommit = True
        msg = simplejson.loads(line)
        # get silo name
        try:
            silo_name = msg['silo']
        except:
            logger.error("Msg badly formed %s\n"%str(msg))
            rq.task_complete()
            continue
        
        # Re-initialize granary
        if silo_name not in silos and not msg['type'] == "d":
            #g = Granary(granary_root)
            #g.state.revert()
            tries = 0
            silos = []
            while tries < 5:
                response = db.getSilos()
                if db.good( response ) :
                    silos = response.results 
                    break
                else:
                    tries += 1
            if silo_name not in silos:
                logger.error("Silo %s does not exist\n"%silo_name)
                rq.task_complete()
                #raise NoSuchSilo
                continue
        if msg['type'] == "c" or msg['type'] == "u" or msg['type'] == "embargo":
            # Creation, update or embargo change
            itemid = msg.get('id', None)
            logger.info("Got creation message on id:%s in silo:%s" % (itemid, silo_name))
            if itemid:
                #Get state infor for dataset
                state_info = {}
                tries = 0
                while tries < 5:
                    response = db.getDatasetState( silo_name, itemid )
                    if db.good( response ) :
                        state_info = response.results 
                        break
                    else:
                        tries += 1
                #Get rdf graph from manifest for dataset
                graph = None
                tries = 0
                while tries < 5:
                    response = db.getFile(silo_name, itemid, 'manifest.rdf')
                    if db.good ( response ) :
                        manifest = response.results
                        graph = ConjunctiveGraph()
                        graph.parse(StringIO(manifest), "xml")
                        break
                    else:
                        tries += 1
                if state_info and graph:
                    solr_doc = gather_document(silo_name, itemid, graph, state_info, debug=True)
                    try:
                        solr.add(_commit=False, **solr_doc)
                    except Exception, e :
                        logger.error("Error adding document to solr id:%s in silo:%s\n" % (itemid, silo_name))
                        try:
                            logger.error("%s\n\n" %str(e))
                        except:
                           pass
                        rq.task_failed()
                        continue
                else:
                    logger.error("Error gathering state and manifest info for id:%s in silo:%s\n" % (itemid, silo_name))
                    rq.task_failed()
                    continue
            else:
                solr_doc = {'id':silo_name, 'silo':silo_name, 'type':'Silo', 'uuid':silo_name}
                #Get state infor for silo
                silo_metadata = {}
                tries = 0
                while tries < 5:
                    response = db.getSiloState( silo_name )
                    if db.good( response ) :
                        silo_metadata = response.results 
                        break
                    else:
                        tries += 1
                solr_doc['title'] = ''
                if 'title' in silo_metadata:
                    solr_doc['title'] = silo_metadata['title']
                solr_doc['description'] = ''
                if 'description' in silo_metadata:
                    solr_doc['description'] = silo_metadata['description']
                solr.add(_commit=False, **solr_doc)
            rq.task_complete()
        elif msg['type'] == "d":
            # Deletion
            itemid = msg.get('id', None)
            if itemid:
                logger.info("Got deletion message on id:%s in silo:%s" % (itemid, silo_name))
                query='silo:"%s" AND id:"%s"'%(silo_name, itemid)
                solr.delete_query(query)
            elif silo_name:
                logger.info("Got deletion message on silo:%s" %silo_name)
                query='silo:"%s"'%silo_name
                solr.delete_query(query)
                #solr.commit()
            rq.task_complete()
