#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains List Dialog Artella Get Dependencies widget implementation
"""

from __future__ import print_function, division, absolute_import

import artella
from artella.core import qtutils

if qtutils.QT_AVAILABLE:
    from artella.externals.Qt import QtCore, QtWidgets, QtGui


class DependenciesListDialog(artella.Dialog, object):
    def __init__(self, parent=None, **kwargs):

        self._do_sync = False
        self._do_recursive = True

        super(DependenciesListDialog, self).__init__(parent, **kwargs)

    @property
    def do_sync(self):
        return self._do_sync

    @property
    def do_recursive(self):
        return self._do_recursive

    def get_main_layout(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        return main_layout

    def setup_ui(self):
        super(DependenciesListDialog, self).setup_ui()

        self.setWindowTitle('Dependencies Found')

        deps_lbl = QtWidgets.QLabel('One or more dependent files are missing: ')
        self._deps_list = QtWidgets.QListWidget()
        cbx_lyt = QtWidgets.QHBoxLayout()
        deps2_lbl = QtWidgets.QLabel('Would you like to download all missing files?')
        self._recursive_cbx = QtWidgets.QCheckBox('Recursive?')
        self._recursive_cbx.setChecked(True)
        cbx_lyt.addWidget(deps2_lbl)
        cbx_lyt.addStretch()
        cbx_lyt.addWidget(self._recursive_cbx)

        self._warning_frame = QtWidgets.QFrame()
        self._warning_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._warning_frame.setFrameShadow(QtWidgets.QFrame.Sunken)
        warning_layout = QtWidgets.QHBoxLayout()
        warning_layout.setSpacing(2)
        warning_layout.setContentsMargins(0, 0, 0, 0)
        self._warning_frame.setLayout(warning_layout)
        warning_icon = QtWidgets.QLabel()
        icon_pixmap = (artella.ResourcesMgr().pixmap('warning') or QtGui.QPixmap()).scaled(
            QtCore.QSize(30, 30), QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
        warning_message = QtWidgets.QLabel(
            'Recursive Get Dependencies can take quite a lot of time when working with big scenes!')
        warning_icon.setPixmap(icon_pixmap)
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_message)
        self._warning_frame.setVisible(self._recursive_cbx.isChecked())

        buttons_layout = QtWidgets.QHBoxLayout()
        self._yes_btn = QtWidgets.QPushButton('Yes')
        self._no_btn = QtWidgets.QPushButton('No')
        buttons_layout.addWidget(self._yes_btn)
        buttons_layout.addWidget(self._no_btn)

        self.main_layout.addWidget(deps_lbl)
        self.main_layout.addWidget(self._deps_list)
        self.main_layout.addLayout(cbx_lyt)
        self.main_layout.addWidget(self._warning_frame)
        self.main_layout.addLayout(buttons_layout)

        self._yes_btn.clicked.connect(self._on_ok)
        self._no_btn.clicked.connect(self._on_cancel)
        self._recursive_cbx.toggled.connect(self._on_toggle_check)

        self.resize(QtCore.QSize(350, 350))

    def set_dependencies(self, deps_list):

        self._deps_list.clear()

        if deps_list is None:
            return

        for dep in deps_list:
            self._deps_list.addItem(dep)

    def _on_ok(self):
        self._do_sync = True
        self._do_recursive = self._recursive_cbx.isChecked()
        self.fade_close()

    def _on_cancel(self):
        self._do_sync = False
        self._do_recursive = True
        self._recursive_cbx.setChecked(self._do_recursive)
        self.fade_close()

    def _on_toggle_check(self, flag):
        self._warning_frame.setVisible(flag)
