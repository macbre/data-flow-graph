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


def format_timestamp(ts):
        """
        Format the UTC timestamp for Elasticsearch
        eg. 2014-07-09T08:37:18.000Z
        @see https://docs.python.org/2/library/time.html#time.strftime
        """
        tz_info = tz.tzutc()
        return datetime.fromtimestamp(ts, tz=tz_info).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def get_log_messages(query, now=None, limit=10000, batch=10000):
	logger = logging.getLogger('get_log_messages')

	# connect to es
	es = Elasticsearch(host='127.0.0.1', port=59200, timeout=120)

	# take logs from the last day and today (last 24h)
	if now is None:
		now = int(time.time())

	indices = ','.join([
		format_index_name(now - 86400),
		format_index_name(now)
	])

	# search
	body = {
		"query": {
			"query_string": {
				"query": query,
			}
		},
		"size": batch,
		"sort": { "@timestamp": { "order": "asc" }}
	}

	items = 0
	since = format_timestamp(now-86400)

	logger.info('Querying for "{}" since {} (limit set to {}, will query in batches of {} items)'.format(query, since, limit, batch))

	while limit is None or items < limit:
		body["filter"] = es_get_timestamp_filer(since)
		res = es.search(index=indices, body=body)

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

		logger.info('Next time will query for logs since {}'.format(since))

	logger.info('Limit of {} results reached, returned {} results so far'.format(limit, items))


def get_query_metadata(query):
	# @see https://pypi.python.org/pypi/sqlparse
	res = None #  sqlparse.parse(query)
	if res:
		statement = res[0]
		sql_type = statement.get_type()  # SELECT, UPDATE, UNKNOWN
		tables = filter(lambda token: isinstance(token, sqlparse.sql.Identifier), statement.tokens)
		tables = map(str, tables)

		print(query[:90], sql_type, tables)

		if sql_type != 'UNKNOWN':
			return sql_type, tables  # SELECT, (products, )

	kind = query.split(' ')[0]

	try:
		# SELECT FROM, INSERT INTO
		matches = re.search(r'(FROM|INTO) (\w+)', query)
		return (kind, (matches.group(2),))
	except:
		pass

	try:
		# UPDATE foo SET ...
		matches = re.search(r'(\w+) SET', query) if 'UPDATE' in query else None
		return (kind, (matches.group(1),))
	except:
		pass

	try:
		# DESCRIBE foo
		matches = re.search(r'DESCRIBE (\w+)', query)
		return (kind, (matches.group(1),))
	except:
		pass

	return None


def extract_metadata(message):
	query = re.sub(r'^SQL ', '', message.get('@message'))
	meta = get_query_metadata(query)

	if meta is None:
		# logger.info('extract_metadata failed: {} - {}'.format(query[:120].encode('utf8'), meta));
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

def unique(fn, iterable):
	# for stats and weighting entries
	c = collections.Counter(iterable)
	max_value = c.most_common(1)[0][1]

	def format_item(item):
		cnt = c[item]

		weight = 1. * cnt / max_value
		if weight < 0.0001:
			weight = 0.0001

		metadata = fn(item, cnt) if fn else ''

		return item + "\t{:.4f}\t{}".format(weight, metadata).rstrip()

	return sorted(map(format_item, iterable))

# take SQL logs from elasticsearch
sql_logs = get_log_messages(query='@message: /SQL.*/', limit=None)  # None - return ALL matching messages

logger.info('Generating metadata...')
meta = map(extract_metadata, sql_logs)
meta = filter(lambda item: item is not None, meta)

logger.info('Building dataflow entries for {} queries...'.format(len(meta)))
entries = map(build_flow_entry, meta)

logger.info('Building TSV file with nodes and edges from {} entries...'.format(len(entries)))
graph = unique(
	lambda entry, cnt: 'QPS: {:.4f}'.format(1. * cnt / 86400),  # calculate QPS
	entries
)

logger.info('Printing out TSV file with {} edges...'.format(len(graph)))

print('# SQL log entries analyzed: {}'.format(len(meta)))
print("\n".join(set(graph)))

# prepare flow data for redis and s3 operations
logger.info("Building dataflow entries for {} redis pushes...")
pushes = map(
	lambda entry: '{source}\t{edge}\t{target}'.format(
		source='bots:{}'.format(entry.get('@source_host').split('.')[0]), edge='push', target='redis:products'),
	get_log_messages(query='program: "elecena.bots" AND @message: "bot::send"',limit=None)
)

pops = map(
	lambda entry: '{source}\t{edge}\t{target}'.format(
		target='mq/request.php', edge='pop', source='redis:products'),
	get_log_messages(query='program: "uportal.bots-worker" AND @message: "Message taken from the queue"',limit=None)
)

graph = unique(
	lambda entry, cnt: '{:.1f} messages/hour'.format(1. * cnt / 24),
	pops + pushes
)

print('# Redis log entries')
print("\n".join(set(graph)))

