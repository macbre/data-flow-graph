"""
Helper functions and classes used to generate data flow graphs
"""
from collections import defaultdict, Counter, OrderedDict


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


def format_tsv_lines(lines):
    """
    Render a set of data into a list of TSV-formatted lines

    :type lines list[dict]
    :rtype: list[str]
    """
    return [format_tsv_line(**line) for line in lines]


def format_graphviz_lines(lines):
    """
    Render a .dot file with graph definition from a given set of data

    :type lines list[dict]
    :rtype: str
    """
    # first, prepare the unique list of all nodes (sources and targets)
    lines_nodes = set()

    for line in lines:
        lines_nodes.add(line['source'])
        lines_nodes.add(line['target'])

    # generate a list of all nodes and their names for graphviz graph
    nodes = OrderedDict()

    for i, node in enumerate(sorted(lines_nodes)):
        nodes[node] = 'n{}'.format(i+1)

    # print(lines_nodes, nodes)

    graph = list()

    # some basic style definition
    graph.append('digraph G {')
    graph.append('\tgraph [ center=true, margin=0.75, nodesep=0.5, ranksep=0.75, rankdir=LR ];')
    graph.append('\tnode [ shape=box, style="rounded,filled" width=0, height=0, '
                 'fontname=Helvetica, fontsize=11 ];')
    graph.append('\tedge [ fontname=Helvetica, fontsize=9 ];')

    # emit nodes definition
    graph.append('\n\t// nodes')

    # https://www.graphviz.org/doc/info/colors.html#brewer
    group_colors = dict()

    for label, name in nodes.items():
        if ':' in label:
            (group, label) = str(label).split(':', 1)

            # register a new group for coloring
            if group not in group_colors:
                group_colors[group] = len(group_colors.keys()) + 1
        else:
            group = None

        graph.append('\t{name} [label="{label}"{group}];'.format(
            name=name,
            label="{}\\n{}".format(group, label) if group is not None else label,
            group=' group="{}" colorscheme=pastel28 color={}'.format(
                group, group_colors[group]) if group is not None else ''
        ))

    # now, connect the nodes
    graph.append('\n\t// edges')
    for line in lines:
        label = line.get('metadata', '')

        graph.append('\t{source} -> {target} [{label}];'.format(
            source=nodes[line['source']],
            target=nodes[line['target']],
            label='label="{}"'.format(label) if label != '' else ''
        ))

    graph.append('}')

    return '\n'.join(graph)


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
