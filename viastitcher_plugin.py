#!/usr/bin/env python

# ViaStitcher for pcbnew
# This is the action plugin interface
# (c) Michele Santucci 2019
#

import wx
import os
import pcbnew

from pcbnew import ActionPlugin, GetBoard
from .viastitcher_dialog import InitViaStitcherDialog
from .localization import _

class ViaStitcherPlugin(ActionPlugin):
    def defaults(self):
        self.name = _(u"ViaStitcher")
        self.category = _(u"Modify PCB")
        self.description = _(u"Create a vias stitching pattern")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'viastitcher.png')

    def Run(self):
        InitViaStitcherDialog(pcbnew.GetBoard())
