from data_flow_graph import format_tsv_line


def test_format():
    assert format_tsv_line('foo', 'select', 'bar') == 'foo\tselect\tbar'
    assert format_tsv_line('foo', 'select', 'bar', value=0) == 'foo\tselect\tbar\t0.0000'
    assert format_tsv_line('foo', 'select', 'bar', value=0.1) == 'foo\tselect\tbar\t0.1000'
    assert format_tsv_line('foo', 'select', 'bar', value=0.12) == 'foo\tselect\tbar\t0.1200'
    assert format_tsv_line('foo', 'select', 'bar', value=0.12, metadata='QPS: 1234') == \
        'foo\tselect\tbar\t0.1200\tQPS: 1234'
