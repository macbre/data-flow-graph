from data_flow_graph import format_graphviz_lines


def test_format():
    lines = [
        {
            'source': 'db:foo:table',
            'edge': 'select',
            'target': 'bar',
        },
        {
            'source': 'foo2',
            'edge': 'select',
            'target': 'web:bar',
            'value': 0.5,
            'metadata': 'test'
        },
        {
            'source': 'web:bar',
            'edge': 'update',
            'target': 'foo2',
            'metadata': 'QPS 4.5'
        }
    ]

    graph = format_graphviz_lines(lines)
    # print(graph)

    with open('examples/graph.gv') as fp:
        assert graph == fp.read().strip()
