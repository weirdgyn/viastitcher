#!/usr/bin/env python

# ViaStitcher for pcbnew
# This is the action plugin interface
# (c) Michele Santucci 2019
#

import wx
import os
import pcbnew
import gettext

from pcbnew import ActionPlugin, GetBoard
from .viastitching_dialog import InitViaStitchingDialog

_ = gettext.gettext

class ViaStitchingPlugin(ActionPlugin):
    def defaults(self):
        self.name = _(u"ViaStitcher")
        self.category = _(u"Modify PCB")
        self.description = _(u"Create a vias stitching pattern")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'viastitching.png')

    def Run(self):
        InitViaStitchingDialog(pcbnew.GetBoard())
