import graphitesend


class GraphiteClient(object):
    def __init__(self, server='127.0.0.1', port=2003, timeout=1, prefix=''):
        self.client = graphitesend.init(graphite_server=server,
                                        graphite_port=port,
                                        timeout_in_seconds=timeout,
                                        prefix=prefix,
                                        system_name='',
                                        clean_metric_name=False)
