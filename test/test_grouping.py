from data_flow_graph import logs_map_and_reduce, format_tsv_line


def _get_logs():
    """
    Return mocked HTTP traffic logs

    :rtype: str[]
    """
    logs = []
    logs += [('web', 'http://serviceA/foo/bar', 'curl')] * 10
    logs += [('web', 'http://serviceA/foo/bar', 'wget')] * 5
    logs += [('web', 'http://serviceB/bar', 'curl')] * 20
    logs += [('cron', 'http://serviceA/test', 'guzzle')] * 5

    return logs


def test_logs_grouping():
    logs = _get_logs()

    # group logs using source name and URL, ignore user agent
    def _map(entry):
        return '{}-{}'.format(entry[0], entry[1])

    # this will be called for each group of logs
    def _reduce(items):
        first = items[0]
        host = str(first[1]).split('/')[2]

        return {
            'source': first[0],
            'edge': 'http',
            'target': host,
            # the following is optional
            'metadata': '{} requests'.format(len(items))
        }

    grouped = logs_map_and_reduce(logs, _map, _reduce)
    # print(grouped)

    assert len(grouped) == 3

    assert grouped[0]['source'] == 'web'
    assert grouped[0]['edge'] == 'http'
    assert grouped[0]['target'] == 'serviceA'
    assert grouped[0]['metadata'] == '15 requests'
    assert grouped[0]['value'] == 0.75

    assert grouped[1]['source'] == 'web'
    assert grouped[1]['edge'] == 'http'
    assert grouped[1]['target'] == 'serviceB'
    assert grouped[1]['metadata'] == '20 requests'
    assert grouped[1]['value'] == 1

    assert grouped[2]['source'] == 'cron'
    assert grouped[2]['edge'] == 'http'
    assert grouped[2]['target'] == 'serviceA'
    assert grouped[2]['metadata'] == '5 requests'
    assert grouped[2]['value'] == 0.25

    assert format_tsv_line(**grouped[0]) == 'web\thttp\tserviceA\t0.7500\t15 requests'
    assert format_tsv_line(**grouped[1]) == 'web\thttp\tserviceB\t1.0000\t20 requests'
    assert format_tsv_line(**grouped[2]) == 'cron\thttp\tserviceA\t0.2500\t5 requests'
