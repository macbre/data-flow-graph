import logging
import sys

from pcapfile import savefile
from pcapfile.protocols.linklayer import ethernet
from pcapfile.protocols.network import ip


logging.basicConfig(level=logging.INFO)


def parse(f):
	logger = logging.getLogger('pcap-to-data-flow')
	logger.info('Reading %s ..', repr(f))

	# @see http://kisom.github.io/pypcapfile/
	capfile = savefile.load_savefile(f, layers=0, verbose=False)

	logger.info('pcap file info: %s', repr(capfile).rstrip().replace('\n', ' / '))

	for packet in capfile.packets:
		try:
			eth_frame = ethernet.Ethernet(packet.raw())

			logger.info(eth_frame)
			ip_packet = ip.IP(eth_frame.payload)

			logger.info(ip_packet)
		except AssertionError:
			logger.error('Error handling a packet', exc_info=True)
			raise


if __name__ == "__main__":
	with open(sys.argv[1], 'rb') as f:
		parse(f)
