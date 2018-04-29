"""
Helper functions and classes used to generate data flow graphs
"""


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
