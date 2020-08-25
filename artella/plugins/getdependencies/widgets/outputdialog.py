#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Artella Get Dependencies custom widgets
"""

from __future__ import print_function, division, absolute_import

import os

import artella
from artella.core import qtutils

if qtutils.QT_AVAILABLE:
    from artella.externals.Qt import QtCore, QtWidgets, QtGui


class DependenciesOutputDialog(artella.Dialog, object):
    def __init__(self, parent=None, **kwargs):
        super(DependenciesOutputDialog, self).__init__(parent, **kwargs)

    def get_main_layout(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        return main_layout

    def setup_ui(self):
        super(DependenciesOutputDialog, self).setup_ui()

        self.setWindowTitle('Get Dependencies Result')

        deps_lbl = QtWidgets.QLabel('Attempting to retrieve the following dependencies: ')
        self._deps_tree = QtWidgets.QTreeWidget()
        self._deps_tree.setHeaderLabels(['Dependency Path'])

        button_layout = QtWidgets.QHBoxLayout()
        self._ok_btn = QtWidgets.QPushButton('Ok')
        button_layout.addStretch()
        button_layout.addWidget(self._ok_btn)
        button_layout.addStretch()

        self.main_layout.addWidget(deps_lbl)
        self.main_layout.addWidget(self._deps_tree)
        self.main_layout.addLayout(button_layout)

        self._ok_btn.clicked.connect(self._on_ok)

        self.resize(QtCore.QSize(350, 350))

    def showEvent(self, event):
        self._deps_tree.expandAll()
        super(DependenciesOutputDialog, self).showEvent(event)

    def add_dependency(self, item_path, parent_path):
        if not item_path:
            return

        new_item = QtWidgets.QTreeWidgetItem()
        new_item.setText(0, item_path)
        if os.path.isfile(item_path):
            new_item.setBackgroundColor(0, QtGui.QColor(80, 120, 110))
        else:
            new_item.setBackgroundColor(0, QtGui.QColor(195, 55, 55))
        if not parent_path:
            self._deps_tree.addTopLevelItem(new_item)
        else:
            parent_item = self._deps_tree.findItems(parent_path, QtCore.Qt.MatchExactly)
            if not parent_item:
                self._deps_tree.addTopLevelItem(new_item)
            else:
                parent_item = parent_item[0]
                parent_item.addChild(new_item)

    def _on_ok(self):
        self.fade_close()
