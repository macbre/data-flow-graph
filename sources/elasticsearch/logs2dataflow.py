#!/usr/bin/env python2
"""
This script demonstates how to transform SQL logs fetched from elasticsearch into graph showing how data flows between the code and the storage
"""
from __future__ import print_function

import time
import logging
import re

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


def extract_table_from_query(query):
	matches = re.search(r'(FROM|INTO|UPDATE) (\w+)', query)
	return matches.group(2) if matches else None


def extract_metadata(message):
	query = re.sub(r'^SQL ', '', message.get('@message'))

	# sphinx or mysql?
	db = message.get('@fields').get('database').get('name')

	# code method
	try:
		# legacy DB logger
		method = message.get('@context').get('exception').get('trace')[-2]  # /opt/elecena/backend/mq/request.php:421
		method = '/'.join(method.split('/')[-2:])  # mq/request.php:53
		method = method.replace(':', '::line ')  # mq/request.php::line 53
	except AttributeError:
		method = message.get('@context').get('method')  # Elecena\Services\Sphinx::search

	return dict(
		# query=query,
		db=db if db == 'sphinx' else 'mysql',
		kind=query.split(' ')[0].upper(),
		table=extract_table_from_query(query) or 'products',
		method=method,
		web_request='http_method' in message.get('@fields', {})
	)


def build_flow_entry(meta):
	table = '{}:{}'.format(meta.get('db'),meta.get('table'))
	(cls, edge) = meta.get('method').split('::')
	reads = meta.get('kind') in ['SELECT', 'CALL']

	# code -> method -> DB table (if the code writes to DB)
	# DB -> method -> code (if the code reads to DB)
	return "{source}\t{edge}\t{target}".format(
		source=table if reads else cls,
		edge=edge,
		target=cls if reads else table
	)

# take SQL logs from elasticsearch
messages = get_log_messages(now=int(time.time()), limit=5000)

meta = map(extract_metadata, messages)
graph = map(build_flow_entry, meta)

# import json; print(json.dumps(meta, indent=True))

print("\n".join(set(graph)))
