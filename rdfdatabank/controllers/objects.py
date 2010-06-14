import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from pylons import app_globals
from rdfdatabank.lib.base import BaseController, render
from rdfdatabank.lib.utils import create_new, is_embargoed

from rdfdatabank.lib.conneg import MimeType as MT, parse as conneg_parse

from datetime import datetime, timedelta
from paste.fileapp import FileApp

import re, os

JAILBREAK = re.compile("[\/]*\.\.[\/]*")

import simplejson

log = logging.getLogger(__name__)

class ObjectsController(BaseController):
    def index(self):
        if not request.environ.get('repoze.who.identity'):
            abort(401, "Not Authorised")
        ident = request.environ.get('repoze.who.identity')
        granary_list = app_globals.granary.silos
        c.silos = app_globals.authz(granary_list, ident)
        
        return render('/list_of_archives.html')
        
    def siloview(self, silo):
        if not request.environ.get('repoze.who.identity'):
            abort(401, "Not Authorised")
        ident = request.environ.get('repoze.who.identity')
        granary_list = app_globals.granary.silos
        c.silos = app_globals.authz(granary_list, ident)
        if silo not in c.silos:
            abort(403, "Forbidden")
        
        c.silo_name = silo
        c.silo = app_globals.granary.get_rdf_silo(silo)
        
        http_method = request.environ['REQUEST_METHOD']
        if http_method == "GET":
            c.embargos = {}
            for item in c.silo.list_items():
                c.embargos[item] = is_embargoed(c.silo, item)
            c.items = c.silo.list_items()
            return render('/siloview.html')
        elif http_method == "POST":
            params = request.POST
            if params.has_key("id"):
                if c.silo.exists(params['id']):
                    response.content_type = "text/plain"
                    response.status_int = 409
                    response.status = "409 Conflict: Object Already Exists"
                    return "Object Already Exists"
                else:
                    # Supported params:
                    # id, title, embargoed, embargoed_until, embargo_days_from_now
                    id = params['id']
                    del params['id']
                    item = create_new(c.silo, id, ident['repoze.who.userid'], **params)
                    # TODO b_creation(silo, id)
                    # conneg return
                    accept_list = conneg_parse(request.environ['HTTP_ACCEPT'])
                    if not accept_list:
                        accept_list= [MT("text", "html")]
                    mimetype = accept_list.pop(0)
                    while(mimetype):
                        if str(mimetype) in ["text/html", "text/xhtml"]:
                            # probably a browser - redirect to newly created object
                            redirect_to(controller="objects", action="itemview", silo=silo, id=id)
                        elif str(mimetype) in ["text/plain"]:
                            response.content_type = "text/plain"
                            response.status_int = 201
                            response.status = "201 Created"
                            response.headers.add("Content-Location", item.uri)
                            return "Created"
                    # Whoops - nothing satisfies
                    response.content_type = "text/plain"
                    response.status_int = 201
                    response.headers.add("Content-Location", item.uri)
                    response.status = "201 Created"
                    return "Created"
                    
    def itemview(self, silo, id):
        
        # Check to see if embargo is on:
        c.silo_name = silo
        c.id = id
        c.silo = app_globals.granary.get_rdf_silo(silo)
        
        c.embargoed = False
        if c.silo.exists(id):
            c.item = c.silo.get_item(id)
        
            if c.item.metadata.get('embargoed') not in ["false", 0, False]:
                c.embargoed = True
        c.embargos = {}
        c.embargos[id] = is_embargoed(c.silo, id)
        http_method = request.environ['REQUEST_METHOD']
        
        editor = False
        
        if not (http_method == "GET" and not c.embargoed):
            #identity management if item 
            if not request.environ.get('repoze.who.identity'):
                abort(401, "Not Authorised")
            ident = request.environ.get('repoze.who.identity')  
            granary_list = app_globals.granary.silos
            if ident:
                c.silos = app_globals.authz(granary_list, ident)      
                if silo not in c.silos:
                    abort(403, "Forbidden")
            else:
                abort(403, "Forbidden")
        
            editor = silo in c.silos
        
        # Method determination
        if http_method == "GET":
            if c.silo.exists(id):
                # conneg:
                c.item = c.silo.get_item(id)
                
                c.parts = c.item.list_parts(detailed=True)
                
                accept_list = conneg_parse(request.environ['HTTP_ACCEPT'])
                if not accept_list:
                    accept_list= [MT("text", "html")]
                mimetype = accept_list.pop(0)
                while(mimetype):
                    if str(mimetype) in ["text/html", "text/xhtml"]:
                        return render('/itemview.html')
                    elif str(mimetype) == "application/json":
                        response.content_type = 'application/json; charset="UTF-8"'
                        return simplejson.dumps(c.item.manifest)
                    elif str(mimetype) in ["application/rdf+xml", "text/xml"]:
                        response.content_type = 'application/rdf+xml; charset="UTF-8"'
                        return c.item.rdf_to_string(format="pretty-xml")
                    elif str(mimetype) == "text/rdf+n3":
                        response.content_type = 'text/rdf+n3; charset="UTF-8"'
                        return c.item.rdf_to_string(format="n3")
                    elif str(mimetype) == "application/x-turtle":
                        response.content_type = 'application/x-turtle; charset="UTF-8"'
                        return c.item.rdf_to_string(format="turtle")
                    elif str(mimetype) in ["text/rdf+ntriples", "text/rdf+nt"]:
                        response.content_type = 'text/rdf+ntriples; charset="UTF-8"'
                        return c.item.rdf_to_string(format="nt")
                # Whoops - nothing satisfies
                abort(406)
            else:
                abort(404)
        elif http_method == "POST" and editor:
            params = request.POST
            if not c.silo.exists(id):
                if 'id' in params.keys():
                    del params['id']
                item = create_new(c.silo, id, ident['repoze.who.userid'], **params)
                
                # TODO b_creation(silo, id)
                # conneg return
                accept_list = conneg_parse(request.environ['HTTP_ACCEPT'])
                if not accept_list:
                    accept_list= [MT("text", "html")]
                mimetype = accept_list.pop(0)
                while(mimetype):
                    if str(mimetype) in ["text/html", "text/xhtml"]:
                        # probably a browser - redirect to newly created object
                        redirect_to(controller="objects", action="itemview", silo=silo, id=id)
                    elif str(mimetype) in ["text/plain"]:
                        response.content_type = "text/plain"
                        response.status_int = 201
                        response.status = "201 Created"
                        response.headers.add("Content-Location", item.uri)
                        return "Created"
                # Whoops - nothing satisfies
                response.content_type = "text/plain"
                response.status_int = 201
                response.headers.add("Content-Location", item.uri)
                response.status = "201 Created"
                return "Created"
            elif params.has_key('embargo_change'):
                item = c.silo.get_item(id)
                if params.has_key('embargoed'):
                    item.metadata['embargoed'] = True
                else:
                    #if is_embargoed(c.silo, id)[0] == True:
                    item.metadata['embargoed'] = False
                if params.has_key('embargoed_until'):
                    item.metadata['embargoed_until'] = params['embargoed_until']
                item.sync()
                e, e_d = is_embargoed(c.silo, id, refresh=True)
                # TODO b_change(silo, id)
                response.content_type = "text/plain"
                response.status_int = 200
                return simplejson.dumps({'embargoed':e, 'embargoed_until':e_d})
            else:
                ## TODO apply changeset handling
                ## 1 - store posted CS docs in 'version' "___cs"
                ## 2 - apply changeset to RDF manifest
                ## 3 - update state to reflect latest CS applied
                response.status_int = 204
                return
            
        elif http_method == "DELETE" and editor:
            if c.silo.exists(id):
                c.silo.del_item(id)
                # TODO b_deletion(silo, id)
                response.status_int = 200
                return "{'ok':'true'}"   # required for the JQuery magic delete to succede.
            else:
                abort(404)

    def subitemview(self, silo, id, path):
        # Check to see if embargo is on:
        c.silo_name = silo
        c.id = id
        c.silo = app_globals.granary.get_rdf_silo(silo)
        
        embargoed = False
        if c.silo.exists(id):
            c.item = c.silo.get_item(id)
        
            if c.item.metadata.get('embargoed') not in ["false", 0, False]:
                embargoed = True
        
        http_method = request.environ['REQUEST_METHOD']
        
        editor = False
        
        if not (http_method == "GET" and not embargoed):
            #identity management if item 
            if not request.environ.get('repoze.who.identity'):
                abort(401, "Not Authorised")
            ident = request.environ.get('repoze.who.identity')  
            granary_list = app_globals.granary.silos
            if ident:
                c.silos = app_globals.authz(granary_list, ident)      
                if silo not in c.silos:
                    abort(403, "Forbidden")
            else:
                abort(403, "Forbidden")
        
            editor = silo in c.silos
        
        c.path = path
        
        http_method = request.environ['REQUEST_METHOD']
        
        if http_method == "GET":
            if c.silo.exists(id):
                c.item = c.silo.get_item(id)
                if c.item.isfile(path):
                    fileserve_app = FileApp(c.item.to_dirpath(path))
                    return fileserve_app(request.environ, self.start_response)
                elif c.item.isdir(path):
                    c.parts = c.item.list_parts(path, detailed=True)
                    return render("/subitemview.html")
                else:
                    return render("/nofilehere.html")
        elif http_method == "PUT" and editor:
            if c.silo.exists(id):
                # Pylons loads the request body into request.body...
                # This is not going to work for large files... ah well
                # POST will handle large files as they are pushed to disc,
                # but this won't
                content = request.body
                item = c.silo.get_item(id)
                
                if JAILBREAK.search(path) != None:
                    abort(400, "'..' cannot be used in the path")
                    
                if item.isfile(path):
                    code = 204
                elif item.isdir(path):
                    response.status_int = 403
                    return "Cannot PUT a file on to an existing directory"
                else:
                    code = 201
                
                item.put_stream(path, content)
                
                #if code == 201:
                #    b_creation(silo, id, path)
                #else:
                #    b_change(silo, id, path)
                #if code == 201:
                #    b_creation(silo, id, path)
                #else:
                #    b_change(silo, id, path)
                response.status_int = code
                return
            else:
                # item doesn't exist yet...
                # DECISION: Auto-instantiate object and then put file there?
                #           or error out with perhaps a 404?
                # Going with error out...
                response.status_int = 404
                return "Object %s doesn't exist" % id
        elif http_method == "POST" and editor:
            if c.silo.exists(id):
                # POST... differences from PUT:
                # path = filepath that this acts on, should be dir, or non-existant
                # if path is a file, this will revert to PUT's functionality and
                # overwrite the file, if there is a multipart file uploaded
                # Expected params: filename, file (uploaded file)
                params = request.POST
                item = c.silo.get_item(id)
                filename = params.get('filename')
                upload = params.get('file')
                if JAILBREAK.search(filename) != None:
                    abort(400, "'..' cannot be used in the path or as a filename")
                target_path = path
                if item.isdir(path) and filename:
                    target_path = os.path.join(path, filename)
                
                if item.isfile(target_path):
                    code = 204
                elif item.isdir(target_path):
                    response.status_int = 403
                    return "Cannot POST a file on to an existing directory"
                else:
                    code = 201
                item.put_stream(target_path, upload.file)
                
                #if code == 201:
                #    b_creation(silo, id, target_path)
                #else:
                #    b_change(silo, id, target_path)
                response.status_int = code
                return
            else:
                # item doesn't exist yet...
                # DECISION: Auto-instantiate object and then put file there?
                #           or error out with perhaps a 404?
                # Going with error out...
                response.status_int = 404
                return "Object %s doesn't exist" % id
        elif http_method == "DELETE" and editor:
            if c.silo.exists(id):
                item = c.silo.get_item(id)
                if item.isfile(path):
                    item.del_stream(path)
                    
                    # TODO b_deletion(silo, id, path)
                    response.status_int = 200
                    return "{'ok':'true'}"   # required for the JQuery magic delete to succede.
                elif item.isdir(path):
                    parts = item.list_parts(path)
                    for part in parts:
                        if item.isdir(os.path.join(path, part)):
                            # TODO implement proper recursive delete, with RDF aggregation
                            # updating
                            abort(400, "Directory is not empty of directories")
                    for part in parts:
                        item.del_stream(os.path.join(path, part))
                        # TODO b_deletion(silo, id, os.path.join(path, part))
                    item.del_stream(path)
                    # TODO b_deletion(silo, id, path)
                    response.status_int = 200
                    return "{'ok':'true'}"   # required for the JQuery magic delete to succede.
                else:
                    abort(404)
            else:
                abort(404)
