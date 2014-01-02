from redis import Redis

# get all keys stored in redis
keys = r.keys()

# Delete embargoed info from redis
for key in keys:
    if ':embargoed' in key:
        r.delete(key)

# Get information about redis
r.info()

# Get no. of items to be proecessed by broker
r.llen('silochanges')

# Get no. of items to be proecessed by solr_worker
r.llen('solrindex')

# Get no. of items that eed to be reindexed, after error correction
r.llen('solrindexerror')
