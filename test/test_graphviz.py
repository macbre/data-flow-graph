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


def test_escaping():
    line = {
            'source': 'Foo "bar" test',
            'metadata': '"The Edge"',
            'target': 'Test "foo" 42',
    }

    graph = format_graphviz_lines([line])
    print(graph)

    assert 'n1 [label="Foo \\"bar\\" test"];' in graph, 'Nodes labels are properly escaped'
    assert 'n2 [label="Test \\"foo\\" 42"];' in graph, 'Nodes labels are properly escaped'
    assert 'n1 -> n2 [label="\\"The Edge\\""];' in graph, 'Edges labels are properly escaped'


def test_escaping_with_groups():
    line = {
            'source': 'Foo:Foo "bar" test',
            'metadata': '"The Edge"',
            'target': 'Bar:Test "foo" 42',
    }

    graph = format_graphviz_lines([line])
    print(graph)

    assert 'n1 [label="Bar\\nTest \\"foo\\" 42" group="Bar" colorscheme=pastel28 color=1];' in graph, 'Nodes labels are properly escaped'
    assert 'n2 [label="Foo\\nFoo \\"bar\\" test" group="Foo" colorscheme=pastel28 color=2];' in graph, 'Nodes labels are properly escaped'
