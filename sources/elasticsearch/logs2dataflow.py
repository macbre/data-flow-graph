#!/usr/bin/env python2
"""
This script demonstates how to transform SQL logs fetched from elasticsearch into graph showing how data flows between the code and the storage
"""
from __future__ import print_function

import time
import logging

from datetime import datetime
from dateutil import tz

from elasticsearch import Elasticsearch

logging.basicConfig(level=logging.INFO)


def format_index_name(ts, prefix='syslog-ng_'):
	tz_info = tz.tzutc()

	# e.g. syslog-ng_2017-06-03
	return "{prefix}{date}".format(prefix=prefix, date=datetime.fromtimestamp(ts, tz=tz_info).strftime('%Y-%m-%d'))


def get_log_messages(now, limit=10000):
	logger = logging.getLogger('get_log_messages')

	# connect to es
	es = Elasticsearch(host='127.0.0.1', port=59200)

	# take logs from the last day
	yesterday = now - 86400

	# search
	# Got 850791 results
	query = '@message: /SQL.*/'
	body = {
		"query": {
			"query_string": {
				"query": query,
			}
		},
		"size": limit
	}

	logger.info('Querying for "{}" (limit set to {})'.format(query, limit))

	res = es.search(index=format_index_name(yesterday), body=body)
	logger.info('Got {} results'.format(res['hits']['total']))

	hits = [hit['_source'] for hit in res['hits']['hits']]
	return hits


# take SQL logs from elasticsearch
messages=get_log_messages(now=int(time.time()), limit=50000)

[print(msg.get('@message')[:120]) for msg in messages[:50]]
print(len(messages))

