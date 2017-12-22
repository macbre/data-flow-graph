import logging
import re
import sys

from collections import Counter  # https://docs.python.org/2/library/collections.html#collections.Counter
from socket import gethostbyaddr, herror

from scapy.all import rdpcap


logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
	datefmt="%Y-%m-%d %H:%M:%S"
)

hosts_cache = dict()

def normalize_host(ip):
	def resolve_host(ip):
		logger = logging.getLogger('resolve_host')

		try:
			hostname = gethostbyaddr(ip)[0]
		except herror as e:
			# socket.herror: [Errno 1] Unknown host
			logger.error("Unable to resolve %s: %s", ip, e)
			return ip

		hostname = hostname.split('.')[0]
		logger.info("%s is known as %s", ip, hostname)

		if not hostname.startswith('ap-'):
			return hostname
		else:
			# ap-s200 -> ap-s*
			return re.sub(r'\d+$', '*', hostname)

	if ip not in hosts_cache:
		hosts_cache[ip] = resolve_host(ip)

	return hosts_cache[ip]


def parse_redis_packet(packet):
	(ip, raw) = packet

	# ['*2\r', '$4\r', 'lpop\r', '$30\r', 'mq::elecena_products::messages']
	try:
		(_, _, cmd, _, arg) = str(raw).strip().split('\n')[:5]
		# print(cmd, arg)

		cmd = cmd.strip().lower()
		arg = arg.lower().strip()

		if cmd == 'lpop':
			# take from the queue
			return '{source}\t{edge}\t{target}'.format(
				target=normalize_host(ip.src),
				edge=cmd,
				source=arg
			)
		elif cmd == 'rpush':
			# push the queue
			return '{source}\t{edge}\t{target}'.format(
				source=normalize_host(ip.src),
				edge=cmd,
				target=arg
			)
		else:
			return None

	except ValueError:
		return None


def parse_scribe_packet(packet):
	(ip, raw) = packet

	# \x00\x00\x026\x00\x00\x00\x03Log\x01\x00\x00\x00\x00\x0f\x00\x01\x0c\x00\x00\x00\x01\x0b\x00\x01\x00\x00\x00\x11app_custom_events\x0b\x00\x02\x00\x00
	try:
		if '\x03Log\x01\x00' not in str(raw):
			return None

		matches = re.search(r"([a-z_]+)\x0b\x00\x02\x00\x00", str(raw))

		if not matches:
			# print('Can not parse scribe frame: ' + repr(ip))
			return None

		# print(ip, matches.group(1))

		src = normalize_host(ip.src)
		dst = normalize_host(ip.dst)
		category = matches.group(1)

		# print(src, dst, category)

		if src == 'mq-s2':
			# scribe pushes data out
			return '{source}\t{edge}\tdst:{target}'.format(
				target=dst,
				edge='scribe',
				source=category
			)
		else:
			# data is pushed to scribe
			return 'src:{source}\t{edge}\t{target}'.format(
				target=category,
				edge='scribe',
				source=src
			)

	except ValueError:
		return None


def parse_raw_packet(packet):
	(ip, _) = packet

	return '{source}\t{edge}\t{target}'.format(
		source=normalize_host(ip.src),
		edge='',
		target=normalize_host(ip.dst),
	)


def parse(f, proto=None):
	logger = logging.getLogger('pcap-to-data-flow')
	logger.info('Reading %s as %s proto ...', repr(f), proto)

	# @see http://kisom.github.io/pypcapfile/
	# @see https://stackoverflow.com/questions/42963343/reading-pcap-file-with-scapy
	packets = rdpcap(f)
	packets_count = len(packets)

	packets_time_diff = packets[-1].time - packets[0].time

	logger.info('Packets read: %d / sniffed in %.2f sec / %s', packets_count, packets_time_diff, repr(packets))
	# logger.info('First one: %s', repr(packets[0]))
	# logger.info('Last one: %s', repr(packets[-1]))

	packets = [
		(packet['IP'], packet['Raw'])
		for packet in packets
	]

	# print(packets)

	# protocol specific handling
	if proto == 'redis':
		packets = map(parse_redis_packet, packets)
	elif proto =='scribe':
		packets = map(parse_scribe_packet, packets)
	elif proto is None:
		packets = map(parse_raw_packet, packets)
	else:
		raise Exception('Unsupported proto: %s', proto)

	# remove empty entries
	packets = filter(lambda x: x is not None, packets)

	# and sort starting with the most frequent ones
	stats = Counter(packets)
	(_, top_freq) = stats.most_common(1)[0]  # the most frequent entry with have edge weight = 1

	packets = [
		'{}\t{:.4f}'.format(val, 1. * freq / top_freq)
		for (val, freq) in stats.most_common()
	]

	print('# processed {} packets sniffed in {:.2f} sec as {}'.format(packets_count, packets_time_diff, proto))
	print('\n'.join(packets))


if __name__ == "__main__":
	if len(sys.argv) > 2:
		(pcap_file, proto) = sys.argv[1:3]
	else:
		pcap_file = sys.argv[1]
		proto = None

	parse(pcap_file, proto)
