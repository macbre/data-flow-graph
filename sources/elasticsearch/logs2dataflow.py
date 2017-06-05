#!/usr/bin/env python2
"""
This script demonstates how to transform SQL logs fetched from elasticsearch into graph showing how data flows between the code and the storage
"""
from __future__ import print_function

import collections
import time
import logging
import re

from datetime import datetime
from dateutil import tz

import sqlparse
from elasticsearch import Elasticsearch

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(name)-35s %(levelname)-8s %(message)s',
	datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


def format_index_name(ts, prefix='syslog-ng_'):
	tz_info = tz.tzutc()

	# e.g. syslog-ng_2017-06-03
	return "{prefix}{date}".format(prefix=prefix, date=datetime.fromtimestamp(ts, tz=tz_info).strftime('%Y-%m-%d'))


def es_get_timestamp_filer(since=None):
	# @see https://www.elastic.co/guide/en/elasticsearch/reference/2.3/query-dsl-range-query.html
        return {
            "range": {
                "@timestamp": {
                    "gt": since,
                }
            }
        } if since is not None else {}


def get_log_messages(now, limit=10000, batch=5000):
	logger = logging.getLogger('get_log_messages')

	# connect to es
	es = Elasticsearch(host='127.0.0.1', port=59200, timeout=120)

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
		"size": batch
	}

	logger.info('Querying for "{}" (limit set to {}, will query in batches of {} items)'.format(query, limit, batch))

	items = 0
	since = None

	while limit is None or items < limit:
		body["filter"] = es_get_timestamp_filer(since)
		res = es.search(index=format_index_name(yesterday), body=body)

		# logger.info('search: {}'.format(body))
		# logger.info('got {} results'.format(res['hits']['total']))

		cnt = len(res['hits']['hits'])
		# logger.info('Got {} results'.format(cnt))

		if cnt == 0:
			logger.info('No more results, returned {} results so far'.format(items))
			return

		# yield results one by one
		for hit in res['hits']['hits']:
			items += 1
			since = hit['_source']['@timestamp']

			yield hit['_source']

		# logger.info('Next time will query for logs since {}'.format(since))

	logger.info('Limit of {} results reached, returned {} results so far'.format(limit, items))


def get_query_metadata(query):
	# @see https://pypi.python.org/pypi/sqlparse
	res = None #  sqlparse.parse(query)
	if res:
		statement = res[0]
		sql_type = statement.get_type()  # SELECT, UPDATE, UNKNOWN
		tables = filter(lambda token: isinstance(token, sqlparse.sql.Identifier), statement.tokens)
		tables = map(str, tables)

		print(query[:90], tables)

		if sql_type != 'UNKNOWN':
			return sql_type, tables  # SELECT, (products, )

	kind = query.split(' ')[0]
	matches = re.search(r'(FROM|INTO|UPDATE) (\w+)', query)
	return (kind, (matches.group(2),)) if matches and matches.group(2) is not None else None


def extract_metadata(message):
	query = re.sub(r'^SQL ', '', message.get('@message'))
	meta = get_query_metadata(query)

	# print('extract_metadata', query[:90], meta);

	if meta is None:
		return None

	(kind, table) = meta
	table = table[0]  # TODO: handle more tables

	# sphinx or mysql?
	db = message.get('@fields').get('database').get('name')

	# code method
	try:
		# legacy DB logger
		method = message.get('@context').get('exception').get('trace')[-2]  # /opt/elecena/backend/mq/request.php:421
		method = '/'.join(method.split('/')[-2:])  # mq/request.php:53
		method = '{}::_{}'.format(method.split(':')[0], kind.lower())  # mq/request.php
	except AttributeError:
		method = message.get('@context').get('method')  # Elecena\Services\Sphinx::search

	if '::' not in method:
		method = method + '::_'

	return dict(
		db=db if db == 'sphinx' else 'mysql',
		kind=kind,  # SELECT
		table=table,  # products
		method=method,
		web_request='http_method' in message.get('@fields', {})
	)


def build_flow_entry(meta):
	table = '{}:{}'.format(meta.get('db'),meta.get('table'))
	(cls, edge) = meta.get('method').split('::')
	reads = meta.get('kind') not in ['INSERT', 'UPDATE', 'DELETE']

	# code -> method -> DB table (if the code writes to DB)
	# DB -> method -> code (if the code reads to DB)
	return "{source}\t{edge}\t{target}".format(
		source=table if reads else cls,
		edge=edge,
		target=cls if reads else table
	)

def unique(iterable):
	# for stats and weighting entries
	c = collections.Counter(iterable)
	max_value = c.most_common(1)[0][1]

	def format_item(item):
		cnt = c[item]

		weight = 1. * cnt / max_value
		if weight < 0.0001:
			weight = 0.0001

		# add as edge metadata
		qps = 1. * cnt / 86400

		return item + "\t{:.4f}\tQPS: {:.4f}".format(weight, qps)

	return map(format_item, iterable)

# take SQL logs from elasticsearch
messages = get_log_messages(now=int(time.time()), limit=None)  # None - return ALL matching messages

logger.info('Generating metadata...')
meta = map(extract_metadata, messages)
meta = filter(lambda item: item is not None, meta)

logger.info('Building dataflow entries for {} queries...'.format(len(meta)))
entries = map(build_flow_entry, meta)

logger.info('Building TSV file with nodes and edges from {} entries...'.format(len(entries)))
graph = unique(entries)

logger.info('Printing out TSV file with {} edges...'.format(len(graph)))
print("\n".join(set(graph)))
