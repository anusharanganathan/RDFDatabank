# -*- coding: utf-8 -*-

import os.path
import json as simplejson

from lib.HTTP_request import HTTPRequest
	
__version_info__ = ( 0, 2, 1 )
__version__  = ".".join( map(str, __version_info__) )

class Databank:
	'''
		Connect to a Databank implementation
		
		Responses in the form: 
			{
				'status': status number of result, 
				'reason': reason behind status if error, 
				'results' : results from request
			}
		
		TODO:-
			Check imputs are valid (e.g. valid names, file exists, etc)
			Use dicts for results to make it easier to use (rather than lists).
		
	'''
	
	http = None
	
	def __init__(self, host, username='', password='' ):
		''' Initiate the connection with the databank <host>. Optionally, also <username> and <password>'''
		self.host = host
		self.username = username
		self.password = password
		
		self._initiate_http( self.host, self.username, self.password )
		
		self.expect_type = "application/JSON"
	
	# def initiate( self ):
	#	''' Errrr, not used... '''
	#	if self.http == None:
	#		self._initiate_http( self.host, self.username, self.password )
			
	def _initiate_http( self, host, username, password ):
		self.http = HTTPRequest( endpointhost=host )
		
		if password !='' and username != '':
			self.http.setRequestUserPass( endpointuser=username, endpointpass=password )
		elif username != '':
			self.http.setRequestUserPass( endpointuser=username )

	
	def getSilos( self ):
		''' Get a list of silos on this repository '''
		(response, respdata) = self.http.doHTTP_GET(resource="/silos", expect_type=self.expect_type)
		
		silos = []
		if self.responseGood( response ):
		    silos = simplejson.loads(respdata)
		    
		return self._create_response( response, silos )
		
	def createSilo( self, silo ):
		''' Create a silo in this repository '''
		    
		fields = [ ("silo", silo) ]
		
		(reqtype, reqdata) = self.http.encode_multipart_formdata( fields, [] )
		(response, respdata) = self.http.doHTTP_POST(reqdata, data_type=reqtype, resource="/admin", expect_type=self.expect_type)
		
		return self._create_response( response, None )

	
	def getSiloState( self, silo ):
		''' Get a the state information for the <dataset> within the <silo>'''
		(response, respdata) = self.http.doHTTP_GET(resource="/" + silo + "/states/", expect_type=self.expect_type)
		
		states = {}
		if self.responseGood( response ):
		    states = simplejson.loads(respdata)
		    
		return self._create_response( response, states )	

		
	def getDatasets( self, silo ):
		''' Get a list of datasets within the <silo>'''
		(response, respdata) = self.http.doHTTP_GET(resource="/" + silo, expect_type=self.expect_type)
		
		datasets = []		
		if self.responseGood( response ):
		    datasets = simplejson.loads(respdata)
		    
		return self._create_response( response, datasets )	

		
	def createDataset( self, silo, id, **params):
		''' Create a dataset with <id> in <silo> . Optionally set a <title>, <emborgoed>, <embargoed until> and <isUUID>'''
                fields = [("id", id)]
                for k,v in params.iteritems():
			fields.append((k, v))
		
		(reqtype, reqdata) = self.http.encode_multipart_formdata( fields, [] )
		(response, respdata) = self.http.doHTTP_POST(reqdata, data_type=reqtype, resource="/" + silo +"/datasets", expect_type=self.expect_type)
		
		return self._create_response( response, None )
	
	
	def setEmbargo( self, silo, dataset, embargoed, embargoed_until=None ):
		''' Set the embargo for the <dataset> in <silo>. <embargoed>='true'/'false'. If embargoed_until=None and embargoed='true', it is embargoed indefinitely '''
		fields = [("embargoed",embargoed)]
                if embargoed_until != None:
			fields.append(('embargoed_until', embargoed_until))
		
		(reqtype, reqdata) = self.http.encode_multipart_formdata(fields, [])
		(response, respdata) = self.http.doHTTP_POST(reqdata, data_type=reqtype, resource="/"+ silo +"/datasets/" + dataset, expect_type=self.expect_type)
		
		return self._create_response( response, None )

	
	def getDatasetState( self, silo, dataset ):
		''' Get a the state information for the <dataset> within the <silo>'''
		(response, respdata) = self.http.doHTTP_GET(resource="/" + silo + "/states/" + dataset, expect_type=self.expect_type)
		
		states = {}
		if self.responseGood( response ):
		    states = simplejson.loads(respdata)
		    
		return self._create_response( response, states )	

		
	def uploadFile( self, silo, dataset, filepath, format="application/zip", filename=None ):
		''' Upload the file at <filepath> into the <dataset> in <silo>. Optionally set a format, or give a filename to use in the dataset '''
		if filename == None:
			filename =  os.path.basename( filepath )
		
		zipdata = open(filepath).read()
		files = [ 
		    ("file", filename, zipdata, format ) 
		]
		
		(reqtype, reqdata) = self.http.encode_multipart_formdata([], files)
		(response, respdata) = self.http.doHTTP_POST(reqdata, data_type=reqtype, resource="/"+ silo +"/datasets/" + dataset, expect_type=self.expect_type)
		
		return self._create_response( response, None )
	
	def getFile( self, silo, dataset, path ):
		''' Get a list of datasets within the <silo>'''
		(response, respdata) = self.http.doHTTP_GET(resource="/" + silo + "/datasets/" + dataset + '/' + path, expect_type=self.expect_type)
		
		return self._create_response( response, respdata )


	def _create_response( self, response, results ):
		return type("Response",(), { 'status':response.status, 'reason': response.reason, 'results' : results })
		
	@staticmethod
	def responseGood( response ):
		return Databank.good( response )
		
	@staticmethod
	def good( response ):
		return response.status >= 200 and response.status < 300	
		
	@staticmethod
	def error( response ):
		return not Databank.good( response )
		
if __name__ == '__main__' :
	
	# Example
	databank = Databank( 'databank-vm1.oerc.ox.ac.uk', 'admin', 'test' ) 
	
	silo = "test_silo"
	dataset = "test_dataset"
	
	response = databank.getSilos()
	if Databank.good( response ) and silo in response.results:	
			
		# Create a dataset
		response = databank.createDataset( silo, dataset )
		if Databank.good( response ):
			print "Created dataset."
			

	
