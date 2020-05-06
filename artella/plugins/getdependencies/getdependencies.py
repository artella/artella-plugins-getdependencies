#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Artella Get Dependencies plugin implementation
"""

from __future__ import print_function, division, absolute_import

import os
import time

import artella
from artella import dcc
from artella import logger
from artella.core import plugin, utils


class GetDependenciesPlugin(plugin.ArtellaPlugin, object):

    ID = 'artella-plugins-getdependencies'
    INDEX = 2

    def __init__(self, config_dict=None, manager=None):
        super(GetDependenciesPlugin, self).__init__(config_dict=config_dict, manager=manager)

    def get_dependencies(self, file_path=None, recursive=True, update_paths=False, show_dialogs=True, skip_open=True):
        """
        Returns all dependency files of the given file path and downloads to the latest available version those files
        that are outdated or that does not exist in user local machine.

        :param str or None file_path: Absolute local file path we want to download dependencies of. If not given,
            current DCC scene file will be used.
        :param bool update_paths: Whether or not depends paths in given file path should be updated.
        :param bool recursive: Whether to find dependencies recursively or only in the given DCC file.
        :param bool show_dialogs: Whether UI dialogs should appear or not.
        """

        def _get_dependencies(deps_file_path, parent_path=None, found_files=None):
            """
            Internal function that recursively all dependencies

            :param deps_file_path:
            :param parent_path:
            :param found_files:
            :return:
            """

            if found_files is None:
                found_files = dict()

            deps_file_path = utils.clean_path(deps_file_path)
            local_path = artella_drive_client.translate_path(deps_file_path)

            logger.log_info('Getting Dependencies: {}'.format(local_path))
            found_files.setdefault(parent_path, list())
            if local_path not in found_files[parent_path]:
                found_files[parent_path].append(local_path)

            if not os.path.isfile(local_path):
                artella.DccPlugin().download_file(local_path)
                if not os.path.isfile(local_path):
                    logger.log_warning('Impossible to retrieve following dependency: {}!'.format(local_path))
                    found_files[parent_path].pop(found_files[parent_path].index(local_path))
                    return None
            else:
                is_latest_version = artella_drive_client.file_is_latest_version(local_path)
                if not is_latest_version:
                    artella.DccPlugin().download_file(local_path)

            ext = os.path.splitext(local_path)[-1]
            if ext not in dcc.extensions():
                return None

            parser = artella.Parser()
            deps_file_paths = parser.parse(local_path)

            if recursive:
                for dep_file_path in deps_file_paths:
                    if not os.path.isabs(dep_file_path):
                        dep_file_path = artella_drive_client.relative_path_to_absolute_path(dep_file_path)
                        # dep_file_path = utils.clean_path(
                        #     os.path.join(os.path.dirname(os.path.dirname(local_path)), dep_file_path))
                    _get_dependencies(dep_file_path, parent_path=local_path, found_files=found_files)
            else:
                for dep_file_path in deps_file_paths:
                    found_files.setdefault(local_path, list())
                    found_files[local_path].append(dep_file_path)

            return found_files

        if not self.is_loaded():
            return

        artella_drive_client = artella.DccPlugin().get_client()
        if not artella_drive_client:
            return False

        if not file_path:
            file_path = dcc.scene_name()
            if not file_path:
                msg = 'Please open a file before getting dependencies.'
                logger.log_warning(msg)
                if show_dialogs:
                    dcc.show_warning(title='Artella - Failed to get dependencies', message=msg)
                return False

        if not file_path or not os.path.isfile(file_path):
            msg = 'File "{}" does not exists. Impossible to get dependencies.'.format(file_path)
            logger.log_warning(msg)
            if show_dialogs:
                dcc.show_error('Artella - Failed to get dependencies', msg)
            return False

        file_path = utils.clean_path(file_path)
        depend_file_paths = _get_dependencies(file_path) or list()
        if not depend_file_paths:
            logger.log_info('No dependencies files found in "{}"'.format(file_path))
            return False

        files_to_download = list()
        files_to_update = [file_path]
        for file_paths_list in depend_file_paths.values():
            for pth in file_paths_list:
                pth = utils.clean_path(pth)
                files_to_update.append(pth)
                if pth not in files_to_download:
                    file_status = artella_drive_client.status(pth)
                    if not file_status or not file_status[0]:
                        continue
                    files_to_download.append(pth)
        artella_drive_client.download(files_to_download)

        # We force the waiting to a high value, otherwise Artella Drive Client will return that no download
        # is being processed
        time.sleep(1.0)

        dcc_progress_bar = artella.ProgressBar()
        dcc_progress_bar.start()
        while True:
            if dcc_progress_bar.is_cancelled():
                artella_drive_client.pause_downloads()
                break
            progress, fd, ft, bd, bt = artella_drive_client.get_progress()
            progress_status = '{} of {} KiB downloaded\n{} of {} files downloaded'.format(
                int(bd / 1024), int(bt / 1024), fd, ft)
            dcc_progress_bar.set_progress_value(value=progress, status=progress_status)
            if progress >= 100 or bd == bt:
                break

        dcc_progress_bar.end()

        if update_paths:
            files_to_update = list(set(files_to_update))
            artella.DccPlugin().update_paths(files_to_update, show_dialogs=show_dialogs, call_post_function=False)

        self._post_get_dependencies()

    def get_non_available_dependencies(self, file_path=None):
        """
        Returns all dependency files that are not in the local machine of the user.

        :param str or None file_path: Absolute local file path we want to get non available dependencies of. If not
            given, current DCC scene file will be used.
        :return: List of non available dependencies for the given file.
        :rtype: list(str)
        """

        non_available_deps = list()

        artella_drive_client = artella.DccPlugin().get_client()
        if not artella_drive_client:
            return non_available_deps

        if not file_path:
            file_path = dcc.scene_name()
        if not file_path or not os.path.isfile(file_path):
            logger.log_warning(
                'Unable to get available non available dependencies. Given scene file does not exists!'.format(
                    file_path))
            return non_available_deps

        parser = artella.Parser()
        deps_file_paths = parser.parse(file_path) or list()
        if not deps_file_paths:
            return non_available_deps

        for dep_file_path in deps_file_paths:
            if dep_file_path and not os.path.isfile(dep_file_path):
                non_available_deps.append(dep_file_path)

        return non_available_deps

    def _post_get_dependencies(self, **kwargs):
        """
        Internal function that is called after get dependencies functionality is over. Can be override in custom DCC
        plugins.
        """

        pass
