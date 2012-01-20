from rdfdatabank.lib.utils import allowable_id2, create_new
from sss import SwordServer, Authenticator, Auth, ServiceDocument, SDCollection, DepositResponse, SwordError, EntryDocument, Statement
from sss.negotiator import AcceptParameters, ContentType

from pylons import app_globals as ag

import uuid, re, logging, urllib
from datetime import datetime

ssslog = logging.getLogger(__name__)

JAILBREAK = re.compile("[\/]*\.\.[\/]*")

class SwordDataBank(SwordServer):
    """
    The main SWORD Server class.  This class deals with all the CRUD requests as provided by the web.py HTTP
    handlers
    """
    def __init__(self, config, auth):
        # get the configuration
        self.config = config
        self.auth_credentials = auth
        
        self.um = URLManager(config)

    def container_exists(self, path):
        # FIXME: rationalise this method with the url manager's role to interpret
        # paths appropriately
        
        # first thing to do is deconstruct the path into silo/dataset
        silo, dataset_id = path.split("/", 1)
        
        if dataset_id.endswith(".rdf"):
            dataset_id = dataset_id[:-4]
        elif dataset_id.endswith(".atom"):
            dataset_id = dataset_id[:-5]
        
        if not ag.granary.issilo(silo):
            return False

        silos = ag.granary.silos
        
        # FIXME: incorporate authentication
        #silos = ag.authz(granary_list, ident)      
        if silo not in silos:
            return False
        
        # get a full silo object
        rdf_silo = ag.granary.get_rdf_silo(silo)
        
        if not rdf_silo.exists(dataset_id):
            return False
            
        return True

    def media_resource_exists(self, path):
        raise NotImplementedError()

    def service_document(self, path=None):
        """
        Construct the Service Document.  This takes the set of collections that are in the store, and places them in
        an Atom Service document as the individual entries
        """
        service = ServiceDocument(version=self.config.sword_version,
                                    max_upload_size=self.config.max_upload_size)
        
        # FIXME: at the moment, there is not authentication, so this is the
        # full list of silos
        
        # now for each collection create an sdcollection
        collections = []
        for col_name in ag.granary.silos:
            href = self.um.silo_url(col_name)
            title = col_name
            mediation = self.config.mediation
            
            # content types accepted
            accept = []
            multipart_accept = []
            if not self.config.accept_nothing:
                if self.config.app_accept is not None:
                    for acc in self.config.app_accept:
                        accept.append(acc)
                
                if self.config.multipart_accept is not None:
                    for acc in self.config.multipart_accept:
                        multipart_accept.append(acc)
                        
            # SWORD packaging formats accepted
            accept_package = []
            for format in self.config.sword_accept_package:
                accept_package.append(format)
            
            col = SDCollection(href=href, title=title, accept=accept, multipart_accept=multipart_accept,
                                accept_package=accept_package, mediation=mediation)
                                
            collections.append(col)
        
        service.add_workspace("Silos", collections)

        # serialise and return
        return service.serialise()
        
        """
        This is our reference for the service document - a list of silos appropriate to the user
        def authz(granary_list,ident):
            g = ag.granary
            g.state.revert()
            g._register_silos()
            granary_list = g.silos
            def _parse_owners(silo_name):
                kw = g.describe_silo(silo_name)
                if "owners" in kw.keys():
                    owners = [x.strip() for x in kw['owners'].split(",") if x]
                    return owners
                else:
                    return []
            #For auth, the code is looking at the list of owners against each silo and not looking at the owner list against each user. A '*' here is meaningless.
            #TODO: Modify code to look at both and keep both silo owner and silos a user has acces to in users.py in sunc and use both
            if ident['role'] == "admin":
                authd = []
                for item in granary_list:
                    owners = _parse_owners(item)
                    if '*' in owners:
                        return granary_list
                    if ident['repoze.who.userid'] in owners:
                        authd.append(item)
                return authd
            else:
                authd = []
                for item in granary_list:
                    owners = _parse_owners(item)
                    if ident['repoze.who.userid'] in owners:
                        authd.append(item)
                return authd
        """

    def list_collection(self, path):
        """
        List the contents of a collection identified by the supplied id
        """
        raise NotImplementedError()

    def deposit_new(self, silo, deposit):
        """
        Take the supplied deposit and treat it as a new container with content to be created in the specified collection
        Args:
        -collection:    the ID of the collection to be deposited into
        -deposit:       the DepositRequest object to be processed
        Returns a DepositResponse object which will contain the Deposit Receipt or a SWORD Error
        """
        # FIXME: where should we check MD5 checksums?  Could be costly to do this
        # inline with large files
        
        # FIXME: do we care if an On-Behalf-Of deposit is made, but mediation is
        # turned off?  And should this be pushed up to the pylons layer?

        # get the list of silos
        silos = ag.granary.silos
        
        # FIXME: get the auth list of silos
        # silos = ag.authz(granary_list, ident)
        
        # does the collection/silo exist?  If not, we can't do a deposit
        if silo not in silos:
            # FIXME: if it exists, but we can't deposit, we need to 403
            raise SwordError(status=404, empty=True)

        # get a full silo object
        rdf_silo = ag.granary.get_rdf_silo(silo)

        # weed out unacceptable deposits
        if deposit.slug is None:
            deposit.slug = str(uuid.uuid4())
        if rdf_silo.exists(deposit.slug):
            raise SwordError(error_uri=DataBankErrors.dataset_conflict, msg="A Dataset with the name " + deposit.slug + " already exists")
        if not allowable_id2(deposit.slug):
            raise SwordError(error_uri=Errors.bad_request, msg="Dataset name can contain only the following characters - " + 
                                                                ag.naming_rule + " and has to be more than 1 character")
        
        # FIXME: we need to extract from the deposit itself the metadata that the item needs
        # and to put them into the params (which is currently an empty dict)
        
        # FIXME: creator needs to be passed in from ident - currently passing empty string
        item = create_new(rdf_silo, deposit.slug, "", {})
        
        # FIXME: username involved here too
        # Broadcast change as message
        ag.b.creation(silo, deposit.slug, ident="")

        # FIXME: probably use the entry ingester to generate the metadata dictionary to pass to create_new
        # store the incoming atom document if necessary
        #if deposit.atom is not None:
        #    entry_ingester = self.configuration.get_entry_ingester()(self.dao)
        #    entry_ingester.ingest(collection, id, deposit.atom)

        # NOTE: left in for reference for the time being, but deposit_new 
        # only support entry only deposits in databank.  This will need to be
        # re-introduced for full sword support
        # store the content file if one exists, and do some processing on it
        #deposit_uri = None
        #derived_resource_uris = []
        #if deposit.content is not None:
        
       #     if deposit.filename is None:
       #         deposit.filename = "unnamed.file"
       #     fn = self.dao.store_content(collection, id, deposit.content, deposit.filename)

            # now that we have stored the atom and the content, we can invoke a package ingester over the top to extract
            # all the metadata and any files we want
            
            # FIXME: because the deposit interpreter doesn't deal with multipart properly
            # we don't get the correct packaging format here if the package is anything
            # other than Binary
       #     ssslog.info("attempting to load ingest packager for format " + str(deposit.packaging))
       #     packager = self.configuration.get_package_ingester(deposit.packaging)(self.dao)
       #     derived_resources = packager.ingest(collection, id, fn, deposit.metadata_relevant)

            # An identifier which will resolve to the package just deposited
       #     deposit_uri = self.um.part_uri(collection, id, fn)
            
            # a list of identifiers which will resolve to the derived resources
       #     derived_resource_uris = self.get_derived_resource_uris(collection, id, derived_resources)

        # the aggregation uri
        agg_uri = self.um.agg_uri(silo, deposit.slug)

        # the Edit-URI
        edit_uri = self.um.edit_uri(silo, deposit.slug)

        # create the initial statement
        s = Statement(aggregation_uri=agg_uri, rem_uri=edit_uri, states=[DataBankStates.initial_state])
        
        # FIXME: need to sort out authentication before we can do this ...
        #by = deposit.auth.by if deposit.auth is not None else None
        #obo = deposit.auth.obo if deposit.auth is not None else None
        #if deposit_uri is not None:
        #    s.original_deposit(deposit_uri, datetime.now(), deposit.packaging, by, obo)
        #s.aggregates = derived_resource_uris

        # In creating the statement we use the existing manifest.rdf file in the
        # item:
        manifest = item.get_rdf_manifest()
        f = open(manifest.filepath, "r")
        rdf_string = f.read()

        # create the new manifest and store it
        new_manifest = s.serialise_rdf(rdf_string)
        item.put_stream("manifest.rdf", new_manifest)

        # create the basic deposit receipt (which involves getting hold of the item's metadata first if it exists)
        #entry_disseminator = self.configuration.get_entry_disseminator()()
        #dc_metadata, other_metadata = entry_disseminator.disseminate(item)
        
        receipt = self.deposit_receipt(silo, deposit.slug, item, "created new item")

        # FIXME: while we don't have full text deposit, we don't need to augment
        # the deposit receipt
        
        # now augment the receipt with the details of this particular deposit
        # this handles None arguments, and converts the xml receipt into a string
        # receipt = self.augmented_receipt(receipt, deposit_uri, derived_resource_uris)
        
        # finally, assemble the deposit response and return
        dr = DepositResponse()
        dr.receipt = receipt.serialise()
        dr.location = receipt.edit_uri
        
        return dr

        """
        This is our reference for deposit_new ...
        
        params = request.POST
            if params.has_key("id"):
                if c_silo.exists(params['id']):
                    response.content_type = "text/plain"
                    response.status_int = 409
                    response.status = "409 Conflict: Dataset Already Exists"
                    return "Dataset Already Exists"
                else:
                    # Supported params:
                    # id, title, embargoed, embargoed_until, embargo_days_from_now
                    id = params['id']
                    if not allowable_id2(id):
                        response.content_type = "text/plain"
                        response.status_int = 403
                        response.status = "403 Forbidden"
                        return "Dataset name can contain only the following characters - %s and has to be more than 1 character"%ag.naming_rule
                    del params['id']
                    item = create_new(c_silo, id, ident['repoze.who.userid'], **params)
                    
                    # Broadcast change as message
                    ag.b.creation(silo, id, ident=ident['repoze.who.userid'])
                    
                    # conneg return
                    accept_list = None
                    if 'HTTP_ACCEPT' in request.environ:
                        try:
                            accept_list = conneg_parse(request.environ['HTTP_ACCEPT'])
                        except:
                            accept_list= [MT("text", "html")]
                    if not accept_list:
                        accept_list= [MT("text", "html")]
                    mimetype = accept_list.pop(0)
                    while(mimetype):
                        if str(mimetype).lower() in ["text/html", "text/xhtml"]:
                            redirect_to(controller="datasets", action="datasetview", silo=silo, id=id)
                        elif str(mimetype).lower() in ["text/plain", "application/json"]:
                            response.content_type = "text/plain"
                            response.status_int = 201
                            response.status = "201 Created"
                            response.headers["Content-Location"] = url(controller="datasets", action="datasetview", silo=silo, id=id)
                            return "201 Created"
                        try:
                            mimetype = accept_list.pop(0)
                        except IndexError:
                            mimetype = None
                    # Whoops - nothing satisfies - return text/plain
                    response.content_type = "text/plain"
                    response.status_int = 201
                    response.headers["Content-Location"] = url(controller="datasets", action="datasetview", silo=silo, id=id)
                    response.status = "201 Created"
                    return "201 Created"
        """

    def get_media_resource(self, path, accept_parameters):
        """
        Get a representation of the media resource for the given id as represented by the specified content type
        -id:    The ID of the object in the store
        -content_type   A ContentType object describing the type of the object to be retrieved
        """
        raise NotImplementedError()
    
    def replace(self, path, deposit):
        """
        Replace all the content represented by the supplied id with the supplied deposit
        Args:
        - oid:  the object ID in the store
        - deposit:  a DepositRequest object
        Return a DepositResponse containing the Deposit Receipt or a SWORD Error
        """
        # FIXME: where should we check MD5 checksums?  Could be costly to do this
        # inline with large files
        
        # FIXME: do we care if an On-Behalf-Of deposit is made, but mediation is
        # turned off?  And should this be pushed up to the pylons layer?

        # first thing to do is deconstruct the path into silo/dataset
        silo, dataset_id = path.split("/", 1)
        
        if not ag.granary.issilo(silo):
            return SwordError(status=404, empty=True)

        silos = ag.granary.silos
        
        # FIXME: incorporate authentication
        #silos = ag.authz(granary_list, ident)      
        if silo not in silos:
            # FIXME: if it exists, but we can't deposit, we need to 403
            raise SwordError(status=404, empty=True)
        
        # get a full silo object
        rdf_silo = ag.granary.get_rdf_silo(silo)
        
        if not rdf_silo.exists(dataset_id):
            raise SwordError(status=404, empty=True)
            
        # now get the dataset object itself
        dataset = rdf_silo.get_item(dataset_id)
        
        # deal with possible problems with the filename
        if deposit.filename is None or deposit.filename == "":
            raise SwordError(error_uri=Errors.bad_request, msg="You must supply a filename to unpack")
        if JAILBREAK.search(deposit.filename) != None:
            raise SwordError(error_uri=Errors.bad_request, msg="'..' cannot be used in the path or as a filename")
        
        
        
        # FIXME: at the moment this metadata operation is not supported by DataBank
        # first figure out what to do about the metadata
        keep_atom = False
        #if deposit.atom is not None:
        #    ssslog.info("Replace request has ATOM part - updating")
        #    entry_ingester = self.configuration.get_entry_ingester()(self.dao)
        #    entry_ingester.ingest(collection, id, deposit.atom)
        #    keep_atom = True
            
        deposit_uri = None
        derived_resource_uris = []
        if deposit.content is not None:
            ssslog.info("Replace request has file content - updating")
            
            # FIXME: how do we do this from DataBank - is it enough to increment the version as below?
            
            # remove all the old files before adding the new.  We always leave
            # behind the metadata; this will be overwritten later if necessary
            #self.dao.remove_content(collection, id, True, keep_atom)
            dataset.increment_version_delta(clone_previous_version=True, copy_filenames=['manifest.rdf'])

            # store the content file
            dataset.put_stream(deposit.filename, deposit.content)
            ssslog.debug("New incoming file stored with filename " + deposit.filename)
            
            # FIXME: this doesn't happen here ... (keeping for the time being for reference)
            
            # now that we have stored the atom and the content, we can invoke a package ingester over the top to extract
            # all the metadata and any files we want.  Notice that we pass in the metadata_relevant flag, so the
            # packager won't overwrite the existing metadata if it isn't supposed to
            #packager = self.configuration.get_package_ingester(deposit.packaging)(self.dao)
            #derived_resources = packager.ingest(collection, id, fn, deposit.metadata_relevant)
            #ssslog.debug("Resources derived from deposit: " + str(derived_resources))
        
            # a list of identifiers which will resolve to the derived resources
            #derived_resource_uris = self.get_derived_resource_uris(collection, id, derived_resources)

            # FIXME: I don't know if this is really how this should be done -
            # need to understand more about the URL space
            
            # An identifier which will resolve to the package just deposited
            deposit_uri = self.um.file_uri(silo, dataset_id, deposit.filename)

        # FIXME: it feels like there's too tight a coupling in DataBank between
        # the web layer and the business logic layer - I have to replicate stuff
        # like this in this controller, rather than rely on some update method
        # in the core to do it for me
        
        # Taken from dataset.py, seems to be the done thing when adding an item.
        dataset.del_triple(dataset.uri, u"dcterms:modified")
        dataset.add_triple(dataset.uri, u"dcterms:modified", datetime.now())
        dataset.del_triple(dataset.uri, u"oxds:currentVersion")
        dataset.add_triple(dataset.uri, u"oxds:currentVersion", dataset.currentversion)
        
        # FIXME: how safe is this?  What other ore:aggregates might there be?
        # we need to back out some of the triples in preparation to update the
        # statement
        dataset.get_rdf_manifest().add_namespace("sword", "http://purl.org/net/sword/terms/")
        aggregates = dataset.list_rdf_objects(dataset.uri, u"ore:aggregates")
        original_deposits = dataset.list_rdf_objects(dataset.uri, u"sword:originalDeposit")
        states = dataset.list_rdf_objects(dataset.uri, u"sword:state")
        
        for a in aggregates:
            dataset.del_triple(a, "*")
        for od in original_deposits:
            dataset.del_triple(od, "*")
        for s in states:
            dataset.del_triple(s, "*")
        dataset.del_triple(dataset.uri, u"ore:aggregates")
        dataset.del_triple(dataset.uri, u"sword:originalDeposit")
        dataset.del_triple(dataset.uri, u"sword:state")
        
        dataset.sync()

        # the aggregation uri
        agg_uri = self.um.agg_uri(silo, dataset_id)

        # the Edit-URI
        edit_uri = self.um.edit_uri(silo, dataset_id)

        # create the statement outline
        s = Statement(aggregation_uri=agg_uri, rem_uri=edit_uri, states=[DataBankStates.populated_state])
        
        # add the aggregation
        s.aggregations = [deposit_uri]
        
        # FIXME: need to sort out authentication before we can do this ...
        #by = deposit.auth.by if deposit.auth is not None else None
        #obo = deposit.auth.obo if deposit.auth is not None else None
        #if deposit_uri is not None:
        #    s.original_deposit(deposit_uri, datetime.now(), deposit.packaging, by, obo)
        
        # NOTE: there are no derived resource uris at this point
        #s.aggregates = derived_resource_uris
        
        # add the original deposit
        s.original_deposit(deposit_uri, datetime.now(), deposit.packaging, None, None)

        # create the new manifest and store it
        manifest = dataset.get_rdf_manifest()
        f = open(manifest.filepath, "r")
        rdf_string = f.read()
        
        new_manifest = s.serialise_rdf(rdf_string)
        dataset.put_stream("manifest.rdf", new_manifest)
        
        # now generate a receipt
        receipt = self.deposit_receipt(silo, dataset_id, dataset, "added zip to dataset")
        
        # now augment the receipt with the details of this particular deposit
        # this handles None arguments, and converts the xml receipt into a string
        receipt = self.augmented_receipt(receipt, deposit_uri, derived_resource_uris)

        # finally, assemble the deposit response and return
        dr = DepositResponse()
        dr.receipt = receipt.serialise()
        dr.location = receipt.edit_uri
        return dr
        """
        Here's our reference for this method:
        
        # File upload by a not-too-savvy method - Service-orientated fallback:
                # Assume file upload to 'filename'
                params = request.POST
                item = c_silo.get_item(id)
                filename = params.get('filename')
                if not filename:
                    filename = params['file'].filename
                upload = params.get('file')
                if JAILBREAK.search(filename) != None:
                    abort(400, "'..' cannot be used in the path or as a filename")
                target_path = filename
                
                if item.isfile(target_path):
                    code = 204
                elif item.isdir(target_path):
                    response.content_type = "text/plain"
                    response.status_int = 403
                    response.status = "403 Forbidden"
                    return "Cannot POST a file on to an existing directory"
                else:
                    code = 201

                if filename == "manifest.rdf":
                    #Copy the uploaded file to a tmp area 
                    mani_file = os.path.join('/tmp', filename.lstrip(os.sep))
                    mani_file_obj = open(mani_file, 'w')
                    shutil.copyfileobj(upload.file, mani_file_obj)
                    upload.file.close()
                    mani_file_obj.close()
                    #test rdf file
                    mani_file_obj = open(mani_file, 'r')
                    manifest_str = mani_file_obj.read()
                    mani_file_obj.close()
                    if not test_rdf(manifest_str):
                        response.status_int = 400
                        return "Bad manifest file"
                    #munge rdf
                    item.increment_version_delta(clone_previous_version=True, copy_filenames=['manifest.rdf'])
                    a = item.get_rdf_manifest()
                    b = a.to_string()
                    munge_manifest(manifest_str, item)
                else:
                    if code == 204:
                        item.increment_version_delta(clone_previous_version=True, copy_filenames=['manifest.rdf', filename])
                    else:
                        item.increment_version_delta(clone_previous_version=True, copy_filenames=['manifest.rdf'])
                    item.put_stream(target_path, upload.file)
                    upload.file.close()
                item.del_triple(item.uri, u"dcterms:modified")
                item.add_triple(item.uri, u"dcterms:modified", datetime.now())
                item.del_triple(item.uri, u"oxds:currentVersion")
                item.add_triple(item.uri, u"oxds:currentVersion", item.currentversion)
                item.sync()
                
                if code == 201:
                    ag.b.creation(silo, id, target_path, ident=ident['repoze.who.userid'])
                    response.status = "201 Created"
                    response.status_int = 201
                    response.headers["Content-Location"] = url(controller="datasets", action="itemview", id=id, silo=silo, path=filename)
                    response_message = "201 Created. Added file %s to item %s" % (filename, id)
                else:
                    ag.b.change(silo, id, target_path, ident=ident['repoze.who.userid'])
                    response.status = "204 Updated"
                    response.status_int = 204
                    response_message = None
        """

    def delete_content(self, path, delete):
        """
        Delete all of the content from the object identified by the supplied id.  the parameters of the delete
        request must also be supplied
        - oid:  The ID of the object to delete the contents of
        - delete:   The DeleteRequest object
        Return a DeleteResponse containing the Deposit Receipt or the SWORD Error
        """
        raise NotImplementedError()
        
    def add_content(self, path, deposit):
        """
        Take the supplied deposit and treat it as a new container with content to be created in the specified collection
        Args:
        -collection:    the ID of the collection to be deposited into
        -deposit:       the DepositRequest object to be processed
        Returns a DepositResponse object which will contain the Deposit Receipt or a SWORD Error
        """
        raise NotImplementedError()

    def get_container(self, path, accept_parameters):
        """
        Get a representation of the container in the requested content type
        Args:
        -oid:   The ID of the object in the store
        -content_type   A ContentType object describing the required format
        Returns a representation of the container in the appropriate format
        """
        # by the time this is called, we should already know that we can return this type, so there is no need for
        # any checking, we just get on with it

        ssslog.info("Container requested in mime format: " + accept_parameters.content_type.mimetype())

        # first thing to do is deconstruct the path into silo/dataset
        silo, dataset_id = path.split("/", 1)
        
        if not ag.granary.issilo(silo):
            return SwordError(status=404, empty=True)

        silos = ag.granary.silos
        
        # FIXME: incorporate authentication
        #silos = ag.authz(granary_list, ident)      
        if silo not in silos:
            # FIXME: if it exists, but we can't deposit, we need to 403
            raise SwordError(status=404, empty=True)
        
        # get a full silo object
        rdf_silo = ag.granary.get_rdf_silo(silo)
        
        if not rdf_silo.exists(dataset_id):
            raise SwordError(status=404, empty=True)
            
        # now get the dataset object itself
        dataset = rdf_silo.get_item(dataset_id)

        # pick either the deposit receipt or the pure statement to return to the client
        if accept_parameters.content_type.mimetype() == "application/atom+xml;type=entry":
            receipt = self.deposit_receipt(silo, dataset_id, dataset, None)
            return receipt.serialise()
        # FIXME: at the moment we don't support conneg on the edit uri
        #elif accept_parameters.content_type.mimetype() == "application/rdf+xml":
        #    return self.dao.get_statement_content(collection, id)
        #elif accept_parameters.content_type.mimetype() == "application/atom+xml;type=feed":
        #    return self.dao.get_statement_feed(collection, id)
        else:
            ssslog.info("Requested mimetype not recognised/supported: " + accept_parameters.content_type.mimetype())
            return None

    def deposit_existing(self, path, deposit):
        """
        Deposit the incoming content into an existing object as identified by the supplied identifier
        Args:
        -oid:   The ID of the object we are depositing into
        -deposit:   The DepositRequest object
        Returns a DepositResponse containing the Deposit Receipt or a SWORD Error
        """
        raise NotImplementedError()

    def delete_container(self, path, delete):
        """
        Delete the entire object in the store
        Args:
        -oid:   The ID of the object in the store
        -delete:    The DeleteRequest object
        Return a DeleteResponse object with may contain a SWORD Error document or nothing at all
        """
        raise NotImplementedError()

    def get_statement(self, path):
        accept_parameters, silo, dataset_id = self.um.interpret_statement_path(path)
        
        if not ag.granary.issilo(silo):
            return SwordError(status=404, msg="silo is not a silo")

        silos = ag.granary.silos
        
        # FIXME: incorporate authentication
        #silos = ag.authz(granary_list, ident)      
        if silo not in silos:
            # FIXME: if it exists, but we can't deposit, we need to 403
            raise SwordError(status=404, msg="silo is not in the allowed list")
        
        # get a full silo object
        rdf_silo = ag.granary.get_rdf_silo(silo)
        
        if not rdf_silo.exists(dataset_id):
            raise SwordError(status=404, msg="dataset does not exist in silo")
            
        # now get the dataset object itself
        dataset = rdf_silo.get_item(dataset_id)
        
        if accept_parameters.content_type.mimetype() == "application/rdf+xml":
            return self.get_rdf_statement(dataset)
        elif accept_parameters.content_type.mimetype() == "application/atom+xml;type=feed":
            return self.get_atom_statement(dataset)
        else:
            return None

    # NOT PART OF STANDARD, BUT USEFUL    
    # These are used by the webpy interface to provide easy access to certain
    # resources.  Not implementing them is fine.  If they are not implemented
    # then you just have to make sure that your file paths don't rely on the
    # Part http handler
     
    def get_part(self, path):
        """
        Get a file handle to the part identified by the supplied path
        - path:     The URI part which is the path to the file
        """
        raise NotImplementedError()
        
    def get_edit_uri(self, path):
        raise NotImplementedError()
    
    def get_rdf_statement(self, dataset):
        # The RDF statement is just the manifest file...
        manifest = dataset.get_rdf_manifest()
        f = open(manifest.filepath, "r")
        return f.read()
        
    def get_atom_statement(self, dataset):
        # FIXME: there isn't a requirement at this stage to support the atom
        # statment for DataBank
        return None
        
    def deposit_receipt(self, silo, identifier, item, treatment, verbose_description=None):
        """
        Construct a deposit receipt document for the provided URIs
        Returns an EntryDocument object
        """
        # FIXME: we don't know what the item's API looks like yet; it's probably
        # from somewhere within RecordSilo or Pairtree.  Suck it and see ...
        
        # assemble the URIs we are going to need
        
        # the atom entry id
        drid = self.um.atom_id(silo, identifier)

        # the Cont-URI
        cont_uri = self.um.cont_uri(silo, identifier)

        # the EM-URI 
        em_uri = self.um.em_uri(silo, identifier)
        em_uris = [(em_uri, None), (em_uri + ".atom", "application/atom+xml;type=feed")]

        # the Edit-URI and SE-IRI
        edit_uri = self.um.edit_uri(silo, identifier)
        se_uri = edit_uri

        # the splash page URI
        splash_uri = self.um.html_url(silo, identifier)

        # the two statement uris
        atom_statement_uri = self.um.state_uri(silo, identifier, "atom")
        ore_statement_uri = self.um.state_uri(silo, identifier, "ore")
        state_uris = [(atom_statement_uri, "application/atom+xml;type=feed"), (ore_statement_uri, "application/rdf+xml")]

        # ensure that there is a metadata object, and that it is populated with enough information to build the
        # deposit receipt
        dc_metadata, other_metadata = self.extract_metadata(item)
        if dc_metadata is None:
            dc_metadata = {}
        if not dc_metadata.has_key("title"):
            dc_metadata["title"] = ["SWORD Deposit"]
        if not dc_metadata.has_key("creator"):
            dc_metadata["creator"] = ["SWORD Client"]
        if not dc_metadata.has_key("abstract"):
            dc_metadata["abstract"] = ["Content deposited with SWORD client"]

        packaging = []
        for disseminator in self.config.sword_disseminate_package:
            packaging.append(disseminator)

        # Now assemble the deposit receipt
        dr = EntryDocument(atom_id=drid, alternate_uri=splash_uri, content_uri=cont_uri,
                            edit_uri=edit_uri, se_uri=se_uri, em_uris=em_uris,
                            packaging=packaging, state_uris=state_uris, dc_metadata=dc_metadata,
                            verbose_description=verbose_description, treatment=treatment)

        return dr
        
    # FIXME: we need to work directly with the RecordSilo code to extract metadata
    # from the item's rdf graph
    def extract_metadata(self, item):
        return {}, {}
        
    def augmented_receipt(self, receipt, original_deposit_uri, derived_resource_uris=[]):
        receipt.original_deposit_uri = original_deposit_uri
        receipt.derived_resource_uris = derived_resource_uris     
        return receipt
    
class DataBankAuthenticator(Authenticator):
    def __init__(self, config): 
        self.config = config
        
    def basic_authenticate(self, username, password, obo):
        # FIXME: we're going to implement a very weak authentication mechanism
        # for the time being
        return Auth(username, obo)
        
# FIXME: we need to discuss with the team a good URL space      
class URLManager(object):
    def __init__(self, config):
        self.config = config
        
    def silo_url(self, silo):
        return self.config.base_url + "silo/" + urllib.quote(silo)
        
    def atom_id(self, silo, identifier):
        # FIXME: this is made up, is there something better?
        return "tag:container@databank/" + urllib.quote(silo) + "/" + urllib.quote(identifier)
        
    def cont_uri(self, silo, identifier):
        return self.config.base_url + "content/" + urllib.quote(silo) + "/" + urllib.quote(identifier)
        
    def em_uri(self, silo, identifier):
        """ The EM-URI """
        return self.config.base_url + "edit-media/" + urllib.quote(silo) + "/" + urllib.quote(identifier)
        
    def edit_uri(self, silo, identifier):
        """ The Edit-URI """
        return self.config.base_url + "edit/" + urllib.quote(silo) + "/" + urllib.quote(identifier)
    
    def agg_uri(self, silo, identifier):
        return self.config.db_base_url + urllib.quote(silo) + "/datasets/" + urllib.quote(identifier)
    
    def html_url(self, silo, identifier):
        """ The url for the HTML splash page of an object in the store """
        # FIXME: what is this really?
        return self.config.base_url + "html/" + urllib.quote(silo) + "/" + urllib.quote(identifier)
    
    def state_uri(self, silo, identifier, type):
        root = self.config.base_url + "statement/" + urllib.quote(silo) + "/" + urllib.quote(identifier)
        if type == "atom":
            return root + ".atom"
        elif type == "ore":
            return root + ".rdf"
            
    def file_uri(self, silo, identifier, filename):
        """ The URL for accessing the parts of an object in the store """
        return self.config.base_url + "file/" + urllib.quote(silo) + "/" + urllib.quote(identifier) + "/" + urllib.quote(filename)
        
    def interpret_statement_path(self, path):
        accept_parameters = None
        if path.endswith("rdf"):
            accept_parameters = AcceptParameters(ContentType("application/rdf+xml"))
            path = path[:-4]
        elif path.endswith("atom"):
            accept_parameters = AcceptParameters(ContentType("application/atom+xml;type=feed"))
            path = path[:-5]
            
        silo, dataset_id = path.split("/", 1)

        return accept_parameters, silo, dataset_id
        
class DataBankErrors(object):
    dataset_conflict = "http://databank.ox.ac.uk/errors/DatasetConflict"
    
class DataBankStates(object):
    initial_state = ("http://databank.ox.ac.uk/state/NewDatasetContainer", "Only the container for the dataset has been created so far")
    populated_state = ("http://databank.ox.ac.uk/state/PopulatedDataset", "The dataset contains content")
