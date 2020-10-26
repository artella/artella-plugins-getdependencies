#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Artella Get Dependencies plugin implementation
"""

from __future__ import print_function, division, absolute_import

import os
import time
import logging

import artella
import artella.dcc as dcc
from artella.core import plugin, utils, qtutils, splash

logger = logging.getLogger('artella')


class GetDependenciesPlugin(plugin.ArtellaPlugin, object):

    ID = 'artella-plugins-getdependencies'
    INDEX = 2

    def __init__(self, config_dict=None, manager=None):
        super(GetDependenciesPlugin, self).__init__(config_dict=config_dict, manager=manager)

    @utils.timestamp
    def get_dependencies(self, file_path=None, recursive=True, update_paths=False, show_dialogs=True):
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

            logger.info('Getting Dependencies: {}'.format(local_path))
            found_files.setdefault(parent_path, list())
            if local_path not in found_files[parent_path]:
                found_files[parent_path].append(local_path)

            if not os.path.isfile(local_path):
                artella.DccPlugin().download_file(local_path)
                if not os.path.isfile(local_path):
                    logger.warning('Impossible to retrieve following dependency: {}!'.format(local_path))
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
                    _get_dependencies(dep_file_path, parent_path=local_path, found_files=found_files)
            else:
                for dep_file_path in deps_file_paths:
                    found_files.setdefault(local_path, list())
                    found_files[local_path].append(dep_file_path)

            return found_files

        res = dict()

        if not self.is_loaded():
            return res

        artella_drive_client = artella.DccPlugin().get_client()
        if not artella_drive_client or not artella_drive_client.check(update=True):
            return res

        if not file_path:
            file_path = dcc.scene_name()
            if not file_path:
                msg = 'Please open a file before getting dependencies.'
                if show_dialogs:
                    artella.DccPlugin().show_warning_message(text=msg, title='Failed to get dependencies')
                else:
                    logger.warning(msg)
                return res

        file_path = utils.clean_path(file_path)
        depend_file_paths = _get_dependencies(file_path) or list()
        if not depend_file_paths:
            logger.warning('No dependencies files found in "{}"'.format(file_path))
            return res
        else:
            res = depend_file_paths

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

        self._download_files(files_to_download, show_dialogs=show_dialogs)

        if update_paths:
            files_to_update = list(set(files_to_update))
            artella.DccPlugin().update_paths(files_to_update, show_dialogs=show_dialogs, call_post_function=False)

        files_updated = [path for path in files_to_download if path and os.path.isfile(path)]
        self._post_get_dependencies(files_updated=files_updated)

        artella.DccPlugin().show_success_message(
            'Get Dependencies operation was successful!', title='Get Depedendencies')

        return res

    def get_non_available_dependencies(self, file_path=None, show_dialogs=True):
        """
        Returns all dependency files that are not in the local machine of the user.

        :param str or None file_path: Absolute local file path we want to get non available dependencies of. If not
            given, current DCC scene file will be used.
        :param bool show_dialogs: Whether UI dialogs should appear or not.
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
            artella.DccPlugin().show_warning_message(
                'Unable to get available non available dependencies. Given scene file does not exists!'.format(
                    file_path))
            return non_available_deps

        parser = artella.Parser()
        deps_file_paths = parser.parse(file_path, show_dialogs=False) or list()

        if not deps_file_paths:
            return non_available_deps

        remote_path_files = dict()

        for dep_file_path in deps_file_paths:
            if dcc.is_udim_path(dep_file_path):
                folder_directory = os.path.dirname(dep_file_path)
                dep_file_name, dep_file_ext = os.path.splitext(os.path.basename(dep_file_path))
                dep_file_parts = dep_file_name.split('_')
                if folder_directory not in remote_path_files:
                    directory_info = artella_drive_client.status(folder_directory, include_remote=True) or None
                    if not directory_info:
                        remote_path_files[folder_directory] = list()
                    else:
                        directory_info = directory_info[0]
                        for handle, data in directory_info.items():
                            remote_info = data.get('remote_info', dict())
                            remote_path_files.setdefault(folder_directory, list())
                            is_file = remote_info.get('raw', dict()).get('type', None) == 'file'
                            name = remote_info.get('name', None)
                            if is_file and name:
                                remote_path_files[folder_directory].append(name)
                if folder_directory in remote_path_files:
                    for directory_path, file_names in remote_path_files.items():
                        if not file_names:
                            continue
                        for file_name in file_names:
                            valid = True
                            file_parts = file_name.split('_')
                            for dep_part, file_part in zip(dep_file_parts, file_parts):
                                if dep_part == '<UDIM>':
                                    continue
                                if dep_part != file_part:
                                    valid = False
                                    break
                            if valid:
                                udim_file_path = os.path.join(directory_path, file_name)
                                translated_path = artella.DccPlugin().translate_path(udim_file_path)
                                if translated_path and not os.path.isfile(translated_path):
                                    if os.path.isdir(translated_path):
                                        continue
                                    file_ext = os.path.splitext(translated_path)
                                    if not file_ext[-1]:
                                        continue
                                    non_available_deps.append(translated_path)
            else:
                translated_path = artella.DccPlugin().translate_path(dep_file_path)
                if translated_path and not os.path.isfile(translated_path):
                    if os.path.isdir(translated_path):
                        continue
                    file_ext = os.path.splitext(translated_path)
                    if not file_ext[-1]:
                        continue
                    non_available_deps.append(translated_path)

        deps_retrieved = list()
        if non_available_deps:
            artella.DccPlugin().show_info_message(
                '{} Missing dependencies found.'.format(len(non_available_deps)), title='Artella - Get Dependencies')
            get_deps = True
            recursive = True
            if show_dialogs:
                get_deps, recursive = self._show_get_deps_dialog(deps=non_available_deps)
            if get_deps:
                if recursive:
                    for non_available_dep in non_available_deps:
                        deps = self.get_dependencies(
                            non_available_dep, recursive=recursive, update_paths=False, show_dialogs=show_dialogs)
                        if deps:
                            deps_retrieved.append(deps)
                        else:
                            deps_retrieved.append({non_available_dep: []})
                else:
                    deps_retrieved = list()
                    self._download_files(non_available_deps, show_dialogs=show_dialogs)
                    for non_available_dep in non_available_deps:
                        deps_retrieved.append({non_available_dep: []})

        if show_dialogs:
            self._show_get_deps_result_dialog(deps_retrieved)

        return non_available_deps

    def _show_get_deps_dialog(self, deps):
        """
        Internal function that shows a dialog that allows the user to select if the want to update missing dependencies
        or not.
        :param deps: List of dependencies files that are missing
        :return: True if the user acceps the operation; False otherwise
        """

        from artella.plugins.getdependencies.widgets import listdialog

        deps_dialog = listdialog.DependenciesListDialog()
        title = 'Artella - Missing dependency' if len(deps) <= 1 else 'Artella - Missing dependencies'
        deps_dialog.setWindowTitle(title)
        deps_dialog.set_dependencies(deps)
        deps_dialog.exec_()

        return deps_dialog.do_sync, deps_dialog.do_recursive

    def _show_get_deps_result_dialog(self, deps_list):
        if not deps_list:
            return

        from artella.plugins.getdependencies.widgets import outputdialog

        deps_dialog = outputdialog.DependenciesOutputDialog()
        for dep in deps_list:
            for dep_parent_path, dep_paths in dep.items():
                if dep_paths:
                    for dep_path in dep_paths:
                            deps_dialog.add_dependency(dep_path, dep_parent_path)
                else:
                    deps_dialog.add_dependency(dep_parent_path, None)
        deps_dialog.show()

    def _download_files(self, files_to_download, show_dialogs=True):

        artella_drive_client = artella.DccPlugin().get_client()
        if not artella_drive_client or not artella_drive_client.check(update=True):
            return

        artella_drive_client.download(files_to_download)

        # We force the waiting to a high value, otherwise Artella Drive Client will return that no download
        # is being processed
        time.sleep(1.0)

        valid_download = True
        if show_dialogs:
            if qtutils.QT_AVAILABLE:
                dcc_progress_bar = splash.ProgressSplashDialog()
            else:
                dcc_progress_bar = artella.ProgressBar()

            dcc_progress_bar.start()
        while True:
            if show_dialogs and dcc_progress_bar.is_cancelled():
                artella_drive_client.pause_downloads()
                valid_download = False
                break
            progress, fd, ft, bd, bt = artella_drive_client.get_progress()
            progress_status = '{} of {} KiB downloaded\n{} of {} files downloaded'.format(
                int(bd / 1024), int(bt / 1024), fd, ft)
            if show_dialogs:
                dcc_progress_bar.set_progress_value(value=progress, status=progress_status)
            if progress >= 100 or bd == bt:
                break

        total_checks = 0
        if valid_download:
            missing_file = False
            for local_file_path in files_to_download:
                if not os.path.exists(local_file_path):
                    missing_file = True
                    break
            while missing_file and total_checks < 5:
                time.sleep(1.0)
                total_checks += 1

        if show_dialogs:
            dcc_progress_bar.end()

    def _post_get_dependencies(self, **kwargs):
        """
        Internal function that is called after get dependencies functionality is over. Can be override in custom DCC
        plugins.
        """

        pass
