#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import logging
import yaml
from os import path
from vmware import vCenter
from graphite import GraphiteClient
from time import clock

cfg = None
vc = None
logger = None


def init_log(path='ViPullAdvStatistics.log', debug=None):
    if debug:
        filelog_level = logging.DEBUG
    else:
        filelog_level = logging.INFO

    logger = logging.getLogger('vmware-graphite-exporter')
    logger.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    filelog = logging.FileHandler(path)
    filelog.setLevel(filelog_level)

    # create formatter and add it to the handlers
    formatter = logging.Formatter(u'%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    filelog.setFormatter(formatter)

    # add the handlers to logger
    logger.addHandler(filelog)

    return logger


def get_config(path):
    try:
        with open(path, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
    except Exception as exc:
        logger.error('Config file error: {}'.format(exc))
        sys.exit(1)
    else:
        return cfg


def main():
    global cfg
    global vc
    global logger

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-c', '--config', required=True,
                           help='configuration file')
    argparser.add_argument('--debug', action='store_true')
    if len(sys.argv) == 1:
        argparser.print_help(sys.stderr)
        sys.exit(1)
    args = argparser.parse_args()

    if not path.isfile(args.config):
        print('VMware to Graphite exporter configuration file {} not found'.format(args.config))
        sys.exit()

    cfg = get_config(args.config)
    logger = init_log(path=cfg['log']['path'], debug=args.debug)

    logger.info('Starting processing vCenter {}'.format(cfg['vmware']['server']))

    try:
        vc = vCenter(cfg['vmware']['server'],
                     cfg['vmware']['username'],
                     cfg['vmware']['password'])
    except Exception as exc:
        logger.error('VMWare vCenter connection error: {}'.format(exc))

    try:
        graphite_client = GraphiteClient(server=cfg['graphite']['server'],
                                         port=cfg['graphite']['port'],
                                         prefix=cfg['graphite']['prefix']).client
    except Exception as exc:
        logger.error('Graphite DB connection error: {}'.format(exc))

    start = clock()
    graphite_client.send_dict(vc.get_vm())
    total = clock() - start
    logger.info("Completion time: {0} seconds.".format(total))


if __name__ == '__main__':
    main()
