pcap
====

## Run `ngrep`

### redis

```
sudo ngrep -d any -q 'mq::' 'port 56379' -n 2000 -O redis.pcap 
```

### scribe

```
sudo ngrep -d any -q '..Log..' port 9090 or 1463 or 5095 or 5088 or 9900 -n 10000 -O scribe.pcap
```

## Process the pcap file

```
python pcap-to-data-flow.py redis.pcap redis > example.tsv
INFO:pcap-to-data-flow:Reading 'redis.pcap' as redis proto ...
INFO:pcap-to-data-flow:Packets read: 2000 in 275.36 sec / <redis.pcap: TCP:2000 UDP:0 ICMP:0 Other:0>
```

```
# processed 2000 packets sniffed in 275.36 sec as redis
mq::elecena_products::messages	lpop	172.17.0.3
86.105.54.80	rpush	mq::elecena_products::messages
mq::elecena_products::messages	lpop	86.105.54.80
86.105.54.80	rpush	mq::elecena_datasheets::message
```
