import json as simplejson
from lib.HTTP_request import HTTPRequest

#--CONFIG-------------------------------------------------------
host = 'databank-vm1.oerc.ox.ac.uk'
username = 'admin'
password = 'test'
datastore = HTTPRequest(endpointhost=host)
datastore.setRequestUserPass(endpointuser=user_name, endpointpass=password)

#--HTTP GET-------------------------------------------------------
#Get a list of silos accessible to the user
(resp, respdata) = datastore.doHTTP_GET(resource="/silos", expect_type="application/JSON")
print "Get list of silos"
print resp.status, resp.reason
if resp.status >= 200 and resp.status < 300:
    silos_list = simplejson.loads(respdata)
    print "number of silos", len(silos_list)
print "-"*40, "\n\n"

#--HTTP GET-------------------------------------------------------
#Get a list of all the datasets in the silo 'sandbox'
(resp, respdata) = datastore.doHTTP_GET(resource="/sandbox", expect_type="application/JSON")
print "Get list of datasets"
print resp.status, resp.reason
if resp.status >= 200 and resp.status < 300:
    dataset_list = simplejson.loads(respdata)
    print "number of datasets", len(dataset_list.keys())
else:
    print "Error getting list of datasets"
print "-"*40, "\n\n"

#--HTTP POST-------------------------------------------------------
#Create a new dataset 'TestSubmission' in the silo 'sandbox'
fields = [ 
    ("id", "TestSubmission")
]
files =[]
(reqtype, reqdata) = datastore.encode_multipart_formdata(fields, files)
(resp, respdata) = datastore.doHTTP_POST(reqdata, data_type=reqtype, resource="/sandbox/datasets", expect_type="application/JSON")
print "Create new dataset"
print resp.status, resp.reason
if resp.status >= 200 and resp.status < 300:
    print respdata
else:
    print "Error creating dataset"
print "-"*40, "\n\n"