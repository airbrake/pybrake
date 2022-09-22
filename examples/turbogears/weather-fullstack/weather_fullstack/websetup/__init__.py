# -*- coding: utf-8 -*-
"""Setup the weather-fullstack application"""

import logging

from weather_fullstack.config.app_cfg import base_config

__all__ = ['setup_app']

log = logging.getLogger(__name__)

from .schema import setup_schema
from .bootstrap import bootstrap


def setup_app(command, conf, vars):
    """Place any commands to setup weather_fullstack here"""
    conf = base_config.configure(conf.global_conf, conf.local_conf)
    base_config.setup(conf)

    setup_schema(command, conf, vars)
    bootstrap(command, conf, vars)
