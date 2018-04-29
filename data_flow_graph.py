"""
Helper functions and classes used to generate data flow graphs
"""
from collections import defaultdict, Counter


def format_tsv_line(source, edge, target, value=None, metadata=None):
    """
    Render a single line for TSV file with data flow described

    :type source str
    :type edge str
    :type target str
    :type value float
    :type metadata str
    :rtype: str
    """
    return '{source}\t{edge}\t{target}\t{value}\t{metadata}'.format(
        source=source,
        edge=edge,
        target=target,
        value='{:.4f}'.format(value) if value is not None else '',
        metadata=metadata or ''
    ).rstrip(' \t')


def logs_map_and_reduce(logs, _map, _reduce):
    """
    :type logs str[]
    :type _map (list) -> str
    :type _reduce (list) -> obj
    """
    keys = []
    mapped_count = Counter()
    mapped = defaultdict(list)

    # first map all entries
    for log in logs:
        key = _map(log)
        mapped[key].append(log)
        mapped_count[key] += 1

        if key not in keys:
            keys.append(key)

    # the most common mapped item
    top_count = mapped_count.most_common(1).pop()[1]

    # now reduce mapped items
    reduced = []

    # keep the order under control
    for key in keys:
        entries = mapped[key]
        # print(key, entries)

        # add "value" field to each reduced item (1.0 will be assigned to the most "common" item)
        item = _reduce(entries)
        item['value'] = 1. * len(entries) / top_count

        reduced.append(item)

    # print(mapped)
    return reduced
