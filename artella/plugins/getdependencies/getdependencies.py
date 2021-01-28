#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Artella Get Dependencies plugin implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging

from artella import dcc, api
from artella.core.dcc import parser
from artella.core import plugin, utils, downloader
from artella.plugins.getdependencies.widgets import listdialog, outputdialog

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

        dependencies = dict()

        if not self.is_loaded():
            return dependencies

        if not api.is_client_available():
            return dependencies

        file_paths = utils.force_list(file_path)
        if not file_paths:
            file_paths = [dcc.scene_name()]
            if not file_paths:
                msg = 'Please open a file before getting dependencies.'
                if show_dialogs:
                    api.show_warning_message(text=msg, title='Failed to get dependencies')
                else:
                    logger.warning(msg)
                return dependencies

        local_paths = list()
        for file_path in file_paths:
            if not file_path:
                continue
            file_path = utils.clean_path(file_path)
            local_path = api.translate_path(file_path)
            local_paths.append(local_path)
        if not local_paths:
            return dependencies

        files_to_download = list()
        for file_path in local_paths:
            if not os.path.isfile(file_path):
                files_to_download.append(file_path)
        if files_to_download:
            dcc_downloader = downloader.Downloader()
            dcc_downloader.download(files_to_download, show_dialogs=show_dialogs)

        valid_paths = list()
        for path in local_paths:
            file_ext = os.path.splitext(file_path)[-1]
            if file_ext not in ('.ma', '.mb'):
                continue
            valid_paths.append(path)
        if not valid_paths:
            return dependencies

        dcc_parser = parser.Parser()
        base_dependencies = dcc_parser.parse(local_paths)
        if not base_dependencies:
            return dependencies

        self._get_dependencies(base_dependencies, dependencies, show_dialogs=show_dialogs, recursive=recursive)

        if update_paths:
            files_to_update = list(set(dependencies))
            api.update_paths(files_to_update, show_dialogs=show_dialogs, call_post_function=False)

        files_updated = list()
        for dependencies_files in list(dependencies.values()):
            for path in dependencies_files:
                if not path or not os.path.isfile(path):
                    continue
                files_updated.append(path)
        self._post_get_dependencies(files_updated=files_updated)

        api.show_success_message('Get Dependencies operation was successful!', title='Get Dependencies')

        return dependencies

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

        if not self.is_loaded():
            return non_available_deps

        if not api.is_client_available():
            return non_available_deps

        if not file_path:
            file_path = dcc.scene_name()
        if not file_path or not os.path.isfile(file_path):
            api.show_warning_message(
                'Unable to get available non available dependencies. Given scene file does not exists!'.format(
                    file_path))
            return non_available_deps

        dcc_parser = parser.Parser()
        deps_file_paths = dcc_parser.parse([file_path], show_dialogs=True) or dict()
        if not deps_file_paths:
            return non_available_deps

        for parent_path, dep_file_paths in deps_file_paths.items():
            for dep_file_path in dep_file_paths:
                if dcc.is_udim_path(dep_file_path):
                    non_available_deps.append(self._get_path_from_udim(dep_file_path))
                else:
                    translated_path = api.translate_path(dep_file_path)
                    if translated_path and not os.path.isfile(translated_path):
                        if os.path.isdir(translated_path):
                            continue
                        file_ext = os.path.splitext(translated_path)
                        if not file_ext[-1]:
                            continue
                        non_available_deps.append(translated_path)

        deps_retrieved = list()
        if non_available_deps:
            api.show_info_message(
                '{} Missing dependencies found.'.format(len(non_available_deps)), title='Artella - Get Dependencies')
            get_deps = True
            recursive = True
            if show_dialogs:
                get_deps, recursive = self._show_get_deps_dialog(deps=non_available_deps)
            if get_deps:
                if recursive:
                    deps = self.get_dependencies(
                        non_available_deps, recursive=recursive, update_paths=False, show_dialogs=show_dialogs)
                    for parent_path, dependencies_files in deps.items():
                        deps_retrieved.append({parent_path: dependencies_files})
                else:
                    deps_retrieved = list()
                    dcc_downloader = downloader.Downloader()
                    dcc_downloader.download(non_available_deps, show_dialogs=show_dialogs)
                    for non_available_dep in non_available_deps:
                        deps_retrieved.append({non_available_dep: []})

        if show_dialogs:
            self._show_get_deps_result_dialog(deps_retrieved)

        return deps_retrieved

    def _show_get_deps_dialog(self, deps):
        """
        Internal function that shows a dialog that allows the user to select if the want to update missing dependencies
        or not.
        :param deps: List of dependencies files that are missing
        :return: True if the user acceps the operation; False otherwise
        """

        deps_dialog = listdialog.DependenciesListDialog()
        title = 'Artella - Missing dependency' if len(deps) <= 1 else 'Artella - Missing dependencies'
        deps_dialog.setWindowTitle(title)
        deps_dialog.set_dependencies(deps)
        deps_dialog.exec_()

        return deps_dialog.do_sync, deps_dialog.do_recursive

    def _show_get_deps_result_dialog(self, deps_list):
        if not deps_list:
            return

        deps_dialog = outputdialog.DependenciesOutputDialog()
        for dep in deps_list:
            for dep_parent_path, dep_paths in dep.items():
                if dep_paths:
                    for dep_path in dep_paths:
                        deps_dialog.add_dependency(dep_path, dep_parent_path)
                else:
                    deps_dialog.add_dependency(dep_parent_path, None)
        deps_dialog.show()

    def _get_dependencies(self, dependency_files, dependencies_, show_dialogs=True, recursive=True):
        files_to_download = list()
        parent_maps = dict()
        for parent_path, dependencies in dependency_files.items():
            dependencies_.setdefault(parent_path, list())
            for dependency_file in dependencies:
                dependency_file = utils.clean_path(dependency_file)
                local_path = api.translate_path(dependency_file)
                if not os.path.isfile(local_path):
                    files_to_download.append(local_path)
                    parent_maps[local_path] = parent_path
                else:
                    is_latest_version = api.file_is_latest_version(local_path)
                    if not is_latest_version:
                        files_to_download.append(local_path)
                        parent_maps[local_path] = parent_path
                    else:
                        dependencies_[parent_path].append(local_path)
        if files_to_download:
            dcc_downloader = downloader.Downloader()
            dcc_downloader.download(files_to_download, show_dialogs=show_dialogs)

        files_to_parse = list()
        for downloaded_file in files_to_download:
            parent_path = parent_maps[downloaded_file]
            dependencies_[parent_path].append(downloaded_file)
            if not os.path.isfile(downloaded_file):
                continue
            file_ext = os.path.splitext(os.path.basename(downloaded_file))[-1]
            if file_ext not in dcc.extensions():
                continue
            files_to_parse.append(downloaded_file)

        if files_to_parse and recursive:
            dcc_parser = parser.Parser()
            if dcc.is_maya():
                deps_file_paths = dcc_parser.parse(
                    files_to_parse, show_dialogs=show_dialogs, force_mayapy_parser=True) or dict()
            else:
                deps_file_paths = dcc_parser.parse(files_to_parse, show_dialogs=show_dialogs) or dict()
            if deps_file_paths:
                self._get_dependencies(deps_file_paths, dependencies_, show_dialogs=show_dialogs)

    def _get_path_from_udim(self, dep_file_path):

        remote_path_files = dict()

        udim_dependencies = list()

        folder_directory = os.path.dirname(dep_file_path)
        dep_file_name, dep_file_ext = os.path.splitext(os.path.basename(dep_file_path))
        dep_file_parts = dep_file_name.split('_')
        if folder_directory not in remote_path_files:
            directory_info = api.file_status(folder_directory, include_remote=True) or None
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
                        translated_path = api.translate_path(udim_file_path)
                        if translated_path and not os.path.isfile(translated_path):
                            if os.path.isdir(translated_path):
                                continue
                            file_ext = os.path.splitext(translated_path)
                            if not file_ext[-1]:
                                continue
                            udim_dependencies.append(translated_path)

        return udim_dependencies

    def _post_get_dependencies(self, **kwargs):
        """
        Internal function that is called after get dependencies functionality is over. Can be override in custom DCC
        plugins.
        """

        pass
