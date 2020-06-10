#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Artella Get Dependencies plugin implementation for Maya
"""

from __future__ import print_function, division, absolute_import

from artella.dccs.maya import utils as maya_utils
from artella.plugins.getdependencies import getdependencies


class GetDependenciesMayaPlugin(getdependencies.GetDependenciesPlugin, object):
    def __init__(self, config_dict=None, manager=None):
        super(GetDependenciesMayaPlugin, self).__init__(config_dict=config_dict, manager=manager)

    def _post_get_dependencies(self, **kwargs):
        """
        Internal function that is called after get dependencies functionality is over. Can be override in custom DCC
        plugins.
        """

        maya_utils.reload_textures()
        maya_utils.reload_dependencies()
