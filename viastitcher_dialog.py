#!/usr/bin/env python

# ViaStitcher for pcbnew
# This is the plugin WX dialog
# (c) Michele Santucci 2019
#
import random
from json import JSONDecodeError

import wx
import pcbnew
import math

from .viastitcher_gui import viastitcher_gui
from .localization import _
from .adaptive_fill import Region, ViaIndex, refill, validate_settings, capsule_section

numpy_available = False
try:
    import numpy as np

    numpy_available = True
except Exception:
    from math import sqrt, pow
import json

__version__ = "0.3.4"
__plugin_name__ = "ViaStitcher"
__plugin_config_key__ = "ViaStitcher"
# Continue accepting the marker written before the public plugin rename.
__legacy_plugin_config_key__ = "ViaStitching"
# __timecode__ = 1972
# This persistent prefix is intentionally unchanged so existing via groups are
# still found and cleared after upgrading to ViaStitcher.
__viagroupname_base__ = "VIA_STITCHING_GROUP"
__plugin_config_layer_name__ = "plugins.config"

GUI_defaults = {
    "to_units": {5: pcbnew.ToMils, 1: pcbnew.ToMM},
    "from_units": {5: pcbnew.FromMils, 1: pcbnew.FromMM},
    "unit_labels": {5: "mils", 1: "mm"},
    "spacing": {5: "40", 1: "1"},
    "offset": {5: "0", 1: "0"},
}

FILL_STYLES = ("Standard", "Stagger", "Randomize")


def _via_width(via, layer=None):
    """KiCad 10 requires a layer when querying padstack-based via diameters."""
    try:
        return via.GetWidth(via.GetLayer() if layer is None else layer)
    except TypeError:
        return via.GetWidth()


class ViaStitcherDialog(viastitcher_gui):
    """Class that gathers all the GUI controls."""

    def __init__(self, board):
        """Initialize the brand new instance."""

        super(ViaStitcherDialog, self).__init__(None)
        self.initialized = False
        self.viagroupname = None
        self.SetTitle(_("{0} v{1}").format(__plugin_name__, __version__))
        self.Bind(wx.EVT_CLOSE, self.onCloseWindow)
        self.m_btnCancel.Bind(wx.EVT_BUTTON, self.onCloseWindow)
        self.m_btnOk.Bind(wx.EVT_BUTTON, self.onProcessAction)
        self.m_btnClear.Bind(wx.EVT_BUTTON, self.onClearAction)
        self.board = board
        self.randomize = False
        self.pcb_group = None
        self.clearance = 0
        self.board_edges = []
        self.config_layer = 0
        self.config_textbox = None
        self.area = None
        self.net = None
        self.config = {}

        self.getConfigLayer()

        for d in pcbnew.GetBoard().GetDrawings():
            if d.GetLayerName() == "Edge.Cuts":
                self.board_edges.append(d)
            if (d.GetLayerName() == __plugin_config_layer_name__
                    or d.GetLayer() == self.config_layer):
                try:
                    new_config = json.loads(d.GetText())
                    if (
                        __plugin_config_key__ in new_config.keys()
                        or __legacy_plugin_config_key__ in new_config.keys()
                    ):
                        self.config_textbox = d
                        self.config = new_config
                except (JSONDecodeError, AttributeError):
                    pass

        # Use the same unit set int PCBNEW
        self.ToUserUnit = None
        self.FromUserUnit = None
        units_mode = pcbnew.GetUserUnits()
        if units_mode == -1:
            wx.MessageBox(_("Not a valid frame"))
            self.Destroy()
            return

        # Check user unit is valid (Mils or MM)
        if units_mode not in GUI_defaults["to_units"]:
            wx.MessageBox(_("Unsupported unit selected"))
            self.Destroy()
            return

        # Check for selected area
        if not self.GetAreaConfig():
            wx.MessageBox(_("Please select a valid area"))
            self.Destroy()
            return

        # Populate nets checkbox
        self.PopulateNets()

        self.ToUserUnit = GUI_defaults["to_units"][units_mode]
        self.FromUserUnit = GUI_defaults["from_units"][units_mode]
        self.m_lblUnit1.SetLabel(_(GUI_defaults["unit_labels"][units_mode]))
        self.m_lblUnit2.SetLabel(_(GUI_defaults["unit_labels"][units_mode]))
        self.m_lblUnit3.SetLabel(_(GUI_defaults["unit_labels"][units_mode]))

        defaults = self.config.get(self.area.GetZoneName(), {})
        self.viagroupname = __viagroupname_base__ + self.area.GetZoneName()

        # Search trough groups
        for group in self.board.Groups():
            if group.GetName() == self.viagroupname:
                self.pcb_group = group

        self.m_txtVSpacing.SetValue(
            defaults.get("VSpacing", GUI_defaults["spacing"][units_mode])
        )
        self.m_txtHSpacing.SetValue(
            defaults.get("HSpacing", GUI_defaults["spacing"][units_mode])
        )
        self.m_txtVOffset.SetValue(
            defaults.get("VOffset", GUI_defaults["offset"][units_mode])
        )
        self.m_txtHOffset.SetValue(
            defaults.get("HOffset", GUI_defaults["offset"][units_mode])
        )
        self.m_txtClearance.SetValue(defaults.get("Clearance", "0"))
        self.m_cbFillStyle.SetSelection(self._get_fill_style_index(defaults))
        self.m_chkAllCopperLayers.SetValue(
            defaults.get("RequireAllCopperLayers", defaults.get("OnlyFilledCopper", False))
        )

        self.m_chkAdaptiveFill.SetValue(defaults.get("AdaptiveFill", False))
        self.m_txtMinSpacing.SetValue(str(defaults.get("MinSpacingPercent", "80")))
        self.m_txtMaxSpacing.SetValue(str(defaults.get("MaxSpacingPercent", "150")))
        self.m_chkAdaptiveFill.Bind(wx.EVT_CHECKBOX, self.onAdaptiveFillChanged)
        self.onAdaptiveFillChanged()

        # Get default Vias dimensions
        via_size = None
        via_drill = None
        for via_dims in self.board.GetViasDimensionsList():
            via_size = via_dims.m_Diameter
            via_drill = via_dims.m_Drill

        # A new board may not have any custom via presets yet. In that case,
        # use the dimensions currently selected in Board Setup.
        if not via_size or not via_drill:
            design_settings = self.board.GetDesignSettings()
            if hasattr(design_settings, "GetCurrentViaSize"):
                via_size = design_settings.GetCurrentViaSize()
            if hasattr(design_settings, "GetCurrentViaDrill"):
                via_drill = design_settings.GetCurrentViaDrill()

        if not via_size or not via_drill:
            wx.MessageBox(
                _("Please set a valid via diameter and drill size in Board Setup")
            )
            self.Destroy()
            return

        self.m_txtViaSize.SetValue("%.6f" % self.ToUserUnit(via_size))
        self.m_txtViaDrillSize.SetValue("%.6f" % self.ToUserUnit(via_drill))
        self.overlappings = None
        self.initialized = True

    @staticmethod
    def _get_fill_style_index(defaults):
        """Read the new style setting or migrate legacy checkbox settings."""
        fill_style = defaults.get("FillStyle")
        if fill_style in FILL_STYLES:
            return FILL_STYLES.index(fill_style)

        # Old configurations could enable both checkboxes. Randomize takes
        # precedence because the new selector intentionally makes styles
        # mutually exclusive.
        if defaults.get("Randomize", False):
            return FILL_STYLES.index("Randomize")
        if defaults.get("Stagger", False):
            return FILL_STYLES.index("Stagger")
        return FILL_STYLES.index("Standard")

    def _get_fill_style(self):
        selection = self.m_cbFillStyle.GetSelection()
        if 0 <= selection < len(FILL_STYLES):
            return FILL_STYLES[selection]
        return "Standard"


    def GetOverlappingItems(self):
        """Collect overlapping items.
        Every bounding box of any item found is a candidate to be inspected for overlapping.
        """

        area_bbox = self.area.GetBoundingBox()

        if hasattr(self.board, "GetModules"):
            modules = self.board.GetModules()
        else:
            modules = self.board.GetFootprints()

        tracks = self.board.GetTracks()

        self.overlappings = []

        for zone in self.board.Zones():
            if zone.GetZoneName() != self.area.GetZoneName():
                if zone.GetNetname() != self.net:
                    if zone.GetBoundingBox().Intersects(area_bbox):
                        self.overlappings.append(zone)

        for item in tracks:
            if (type(item) is pcbnew.PCB_VIA) and (
                item.GetBoundingBox().Intersects(area_bbox)
            ):
                self.overlappings.append(item)
            if type(item) is pcbnew.PCB_TRACK:
                self.overlappings.append(item)

        for item in modules:
            if item.GetBoundingBox().Intersects(area_bbox):
                for pad in item.Pads():
                    self.overlappings.append(pad)
                for zone in item.Zones():
                    self.overlappings.append(zone)

        # TODO: change algorithm to 'If one of the candidate area's edges overlaps with target area declare candidate as overlapping'
        for i in range(0, self.board.GetAreaCount()):
            item = self.board.GetArea(i)
            if item.GetBoundingBox().Intersects(area_bbox):
                if item.GetNetname() != self.net:
                    self.overlappings.append(item)

    def GetAreaConfig(self):
        """Check selected area (if any) and verify if it is a valid container for vias.

        Returns:
            bool: Returns True if an area/zone is selected and matches the implant criteria, False otherwise.
        """

        for i in range(0, self.board.GetAreaCount()):
            area = self.board.GetArea(i)
            if area.IsSelected():
                if not area.IsOnCopperLayer():
                    return False
                elif (
                    hasattr(area, "GetDoNotAllowCopperPour")
                    and area.GetDoNotAllowCopperPour()
                ):
                    return False
                elif (
                    hasattr(area, "GetDoNotAllowZoneFills")
                    and area.GetDoNotAllowZoneFills()
                ):
                    return False
                self.area = area
                self.net = area.GetNetname()
                return True

        return False

    def PopulateNets(self):
        """Populate nets widget."""

        nets = self.board.GetNetsByName()

        # Tricky loop, the iterator should return two values, unluckly I'm not able to use the
        # first value of the couple so I'm recycling it as netname.
        for netname, net in nets.items():
            netname = net.GetNetname()
            if (netname != None) and (netname != ""):
                self.m_cbNet.Append(netname)

        # Select the net used by area (if any)
        if self.net != None:
            index = self.m_cbNet.FindString(self.net)
            self.m_cbNet.Select(index)

    def ClearArea(self):
        """Clear selected area."""

        undo = self.m_chkClearOwn.IsChecked()
        drillsize = self.FromUserUnit(float(self.m_txtViaDrillSize.GetValue()))
        viasize = self.FromUserUnit(float(self.m_txtViaSize.GetValue()))
        netname = self.m_cbNet.GetStringSelection()
        netcode = self.board.GetNetcodeFromNetname(netname)
        # commit = pcbnew.COMMIT()
        viacount = 0

        for item in self.board.GetTracks():
            if type(item) is pcbnew.PCB_VIA:
                # If the user selected the Undo action only signed/grouped vias are removed,
                # otherwise are removed vias matching values set in the dialog.

                # if undo and (item.GetTimeStamp() == __timecode__):
                if undo and (self.pcb_group is not None):
                    group = item.GetParentGroup()
                    if group is not None and group.GetName() == self.viagroupname:
                        self.board.Remove(item)
                        viacount += 1
                        # commit.Remove(item)
                elif (
                    (not undo)
                    and self.area.HitTestFilledArea(
                        self.area.GetLayer(), item.GetPosition(), 0
                    )
                    and (item.GetDrillValue() == drillsize)
                    and (_via_width(item) == viasize)
                    and (item.GetNetname() == netname)
                ):
                    self.board.Remove(item)
                    self.pcb_group.RemoveItem(item)
                    viacount += 1
                    # commit.Remove(item)

        if viacount > 0:
            wx.MessageBox(_("Removed: %d vias!") % viacount)
            # commit.Push()
            pcbnew.Refresh()

    def CheckClearance(self, via, area, clearance):
        """Check if position specified by p1 comply with given clearance in area.

        Parameters:
            p1 (wxPoint): Position to test
            area (pcbnew.ZONE_CONTAINER): Area
            clearance (int): Clearance value

        Returns:
            bool: True if p1 position comply with clearance value False otherwise.

        """
        p1 = via.GetPosition()
        corners = area.GetNumCorners()
        # Calculate minimum distance from corners
        # TODO: remove?
        for i in range(corners):
            corner = area.GetCornerPosition(i)
            # Handle both VECTOR2I and wxPoint
            if hasattr(corner, "getWxPoint"):
                p2 = corner.getWxPoint()
            else:
                p2 = corner  # VECTOR2I can be used directly
            # Avoid subtracting SWIG geometry objects directly: on KiCad 7
            # GetCornerPosition().getWxPoint() may return wxPoint while
            # via.GetPosition() returns VECTOR2I.
            the_distance = math.hypot(
                p2.x - p1.x,
                p2.y - p1.y,
            )

            if the_distance < clearance:
                return False

        for i in range(corners):
            corner1 = area.GetCornerPosition(i)
            corner2 = area.GetCornerPosition((i + 1) % corners)
            # Handle both VECTOR2I and wxPoint
            if hasattr(corner1, "getWxPoint"):
                pc1 = corner1.getWxPoint()
                pc2 = corner2.getWxPoint()
            else:
                pc1 = corner1  # VECTOR2I can be used directly
                pc2 = corner2
            the_distance, _ = pnt2line(p1, pc1, pc2)

            if the_distance <= clearance:
                return False

        for edge in self.board_edges:
            if edge.ShowShape() == "Line":
                the_distance, _ = pnt2line(p1, edge.GetStart(), edge.GetEnd())
                if the_distance <= clearance + _via_width(via) / 2:
                    return False
            if edge.ShowShape() == "Arc":
                # distance from center of Arc and with angle within Arc angle should be outside Arc radius +- clearance + via Width/2
                center = edge.GetPosition()
                start = edge.GetStart()
                end = edge.GetEnd()
                radius = norm(center - end)
                dist = norm(p1 - center)
                if (
                    radius - (self.clearance + _via_width(via) / 2)
                    < dist
                    < radius + (self.clearance + _via_width(via) / 2)
                ):
                    # via is in range need to check the angle
                    start_angle = math.atan2((start - center).y, (start - center).x)
                    end_angle = math.atan2((end - center).y, (end - center).x)
                    if end_angle < start_angle:
                        end_angle += 2 * math.pi
                    point_angle = math.atan2((p1 - center).y, (p1 - center).x)
                    if start_angle <= point_angle <= end_angle:
                        return False

        return True

    def CheckOverlap(self, via):
        """Check if via overlaps or interfere with other items on the board."""

        safe_margin = pcbnew.FromMM(0.35)
        min_hole_dist = pcbnew.FromMM(0.5)

        # --- 0. Edge ccuts check (Edge.Cuts) ---
        # set edge cuts range clearance (es. 0.5 mm)
        edge_clearance = pcbnew.FromMM(0.5)
        check_dist = int(_via_width(via) // 2 + edge_clearance)

        for edge in self.board_edges:
            if edge.HitTest(via.GetPosition(), check_dist):
                return True
        # ---------------------------------------------

        via_bbox = via.GetBoundingBox()
        via_bbox.Inflate(safe_margin)

        for item in self.overlappings:
            # 1. ignore copper filled zones
            if type(item).__name__ in ["ZONE", "FP_ZONE", "PCB_ZONE", "ZONE_CONTAINER"]:
                continue

            # 2. handling of the same net points
            if hasattr(item, "GetNetCode") and item.GetNetCode() == via.GetNetCode():
                if type(item) is pcbnew.PCB_TRACK:
                    continue
                elif type(item) is pcbnew.PCB_VIA:
                    # if same net check clearance
                    dist = math.hypot(
                        via.GetPosition().x - item.GetPosition().x,
                        via.GetPosition().y - item.GetPosition().y,
                    )
                    if dist < (
                        via.GetDrillValue() / 2
                        + item.GetDrillValue() / 2
                        + min_hole_dist
                    ):
                        return True
                    continue

            # 3. check collisions with Pads
            if type(item) is pcbnew.PAD:
                via_layers = set(via.GetLayerSet().Seq())
                pad_layers = set(item.GetLayerSet().Seq())
                common_layers = via_layers & pad_layers
                if common_layers:
                    p = via.GetPosition()
                    accuracy = int(_via_width(via) // 2 + safe_margin)
                    if any(item.HitTest(p, accuracy, layer) for layer in common_layers):
                        return True

            # 4. check collisions with VIAS (other nets)
            elif type(item) is pcbnew.PCB_VIA:
                if item.GetBoundingBox().Intersects(via_bbox):
                    return True

            # 5. check collisions with other tracks (other nets)
            elif type(item) is pcbnew.PCB_TRACK:
                if item.GetBoundingBox().Intersects(via_bbox):
                    width = item.GetWidth()
                    dist, _ = pnt2line(
                        via.GetPosition(), item.GetStart(), item.GetEnd()
                    )
                    if (
                        dist
                        <= self.clearance
                        + width // 2
                        + _via_width(via) / 2
                        + safe_margin
                    ):
                        return True

        return False
        for item in self.overlappings:
            if type(item) is pcbnew.PAD:
                # Check with HitTest() rather than GetBoundingBox() to handle round+custom pad shapes
                via_layers = set(via.GetLayerSet().Seq())
                pad_layers = set(item.GetLayerSet().Seq())
                common_layers = via_layers & pad_layers
                if common_layers:
                    p = via.GetPosition()
                    accuracy = _via_width(via) // 2
                    if any(item.HitTest(p, accuracy, layer) for layer in common_layers):
                        return True
            elif type(item) is pcbnew.PCB_VIA:
                # Overlapping with vias work best if checking is performed by intersection
                if item.GetBoundingBox().Intersects(via.GetBoundingBox()):
                    return True
            elif type(item).__name__ in [
                "ZONE",
                "FP_ZONE",
                "PCB_ZONE",
                "ZONE_CONTAINER",
            ]:
                via_layers = set(via.GetLayerSet().Seq())
                zone_layers = set(item.GetLayerSet().Seq())
                common_layers = via_layers & zone_layers
                if common_layers:
                    p = via.GetPosition()
                    accuracy = _via_width(via) // 2
                    if any(
                        item.HitTestFilledArea(layer, p, accuracy)
                        for layer in common_layers
                    ):
                        return True
            elif type(item) is pcbnew.PCB_TRACK:
                if item.GetBoundingBox().Intersects(via.GetBoundingBox()):
                    width = item.GetWidth()
                    dist, _ = pnt2line(
                        via.GetPosition(), item.GetStart(), item.GetEnd()
                    )
                    if dist <= self.clearance + width // 2 + _via_width(via) / 2:
                        return True
        return False

    def HasFilledCopperAt(self, position, layers, netcode, radius):
        """Return whether the selected net has filled copper around a via."""

        zones = [zone for zone in self.board.Zones() if zone.GetNetCode() == netcode]
        required = len(layers) if self.m_chkAllCopperLayers.GetValue() else 2
        by_layer = [(layer, [zone for zone in zones if layer in zone.GetLayerSet().Seq()])
                    for layer in layers]
        # Reject missing layers before spending boundary samples on other layers.
        candidates = [(layer, zones) for layer, zones in by_layer
                      if any(zone.HitTestFilledArea(layer, position, 0) for zone in zones)]
        if len(candidates) < required:
            return False
        samples = [self._point((position.x + radius * math.cos(i * math.pi / 16),
                                position.y + radius * math.sin(i * math.pi / 16)))
                   for i in range(32)]
        connected = 0
        for layer, zones in candidates:
            if all(any(zone.HitTestFilledArea(layer, sample, 0) for zone in zones)
                   for sample in samples):
                connected += 1
                if connected >= required:
                    return True
        return False

    def _copper_layers(self):
        return [layer for layer in self.board.GetEnabledLayers().Seq()
                if pcbnew.IsCopperLayer(layer)]

    def onAdaptiveFillChanged(self, event=None):
        enabled = self.m_chkAdaptiveFill.GetValue()
        self.m_txtMinSpacing.Enable(enabled)
        self.m_txtMaxSpacing.Enable(enabled)

    def _read_fill_settings(self):
        """Validate everything before assigning a zone name or writing config."""
        def number(control):
            value = float(control.GetValue())
            if not math.isfinite(value):
                raise ValueError("Non-finite value")
            return value

        self.fill_settings = {
            "drill": self.FromUserUnit(number(self.m_txtViaDrillSize)),
            "diameter": self.FromUserUnit(number(self.m_txtViaSize)),
            "pitch": (self.FromUserUnit(number(self.m_txtHSpacing)),
                      self.FromUserUnit(number(self.m_txtVSpacing))),
            "offset": (self.FromUserUnit(number(self.m_txtHOffset)),
                       self.FromUserUnit(number(self.m_txtVOffset))),
            "clearance": self.FromUserUnit(number(self.m_txtClearance)),
            "adaptive": self.m_chkAdaptiveFill.GetValue(),
        }
        settings = self.fill_settings
        settings["minimum"] = number(self.m_txtMinSpacing) / 100 if settings["adaptive"] else 0.8
        settings["maximum"] = number(self.m_txtMaxSpacing) / 100 if settings["adaptive"] else 1.5
        validate_settings(settings["pitch"], settings["diameter"],
                          settings["minimum"], settings["maximum"])
        if not 0 < settings["drill"] < settings["diameter"] or settings["clearance"] < 0:
            raise ValueError("Invalid via geometry or clearance")
        if not self.m_cbNet.GetStringSelection():
            raise ValueError("No net selected")

    def _filled_regions(self):
        """Snapshot the selected zone's real filled outlines and holes per layer."""
        regions = []
        def points(chain):
            return [(chain.CPoint(i).x, chain.CPoint(i).y)
                    for i in range(chain.PointCount())]
        for layer in self.area.GetLayerSet().Seq():
            polygons = self.area.GetFilledPolysList(layer)
            for i in range(polygons.OutlineCount()):
                outline = points(polygons.COutline(i))
                if len(outline) >= 3:
                    regions.append(Region(layer, outline,
                        [points(polygons.CHole(i, j)) for j in range(polygons.HoleCount(i))]))
        return regions

    @staticmethod
    def _point(position):
        point_type = getattr(pcbnew, "VECTOR2I", None) or pcbnew.wxPoint
        return point_type(int(position[0]), int(position[1]))

    def _place_via(self, position):
        """Shared copper/collision checks and bookkeeping for both passes."""
        settings = self.fill_settings
        p = self._point(position)
        layer_set = self.area.GetLayerSet()
        layers = self._copper_layers()
        netcode = self.board.GetNetcodeFromNetname(self.m_cbNet.GetStringSelection())
        if not any(self.area.HitTestFilledArea(layer, p, 0) for layer in layer_set.Seq()):
            return False
        if not self.HasFilledCopperAt(
                p, layers, netcode, settings["diameter"] / 2):
            return False
        via = pcbnew.PCB_VIA(self.board)
        via.SetPosition(p)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNetCode(netcode)
        if hasattr(via, "SetIsFree"):
            via.SetIsFree(True)
        via.SetDrill(settings["drill"] + 2 * self.clearance)
        via.SetWidth(settings["diameter"] + 2 * self.clearance)
        if self.CheckOverlap(via):
            return False
        if self.clearance and not self.CheckClearance(via, self.area, self.clearance):
            return False
        via.SetWidth(settings["diameter"])
        via.SetDrill(settings["drill"])
        self.board.Add(via)
        self.pcb_group.AddItem(via)
        # The original snapshot omitted vias added during this run.
        self.overlappings.append(via)
        return True

    def _refill(self, origin, stagger):
        settings = self.fill_settings
        index = ViaIndex(settings["pitch"])
        netcode = self.board.GetNetcodeFromNetname(self.m_cbNet.GetStringSelection())
        required_layers = set(self._copper_layers())
        # Build configuration-space obstacles once: positions forbidden to a
        # via center, using the same margins as CheckOverlap. These sections
        # guide candidates; the shared placement routine remains authoritative.
        capsules, boxes = [], []
        radius = settings["diameter"]/2 + self.clearance
        margin = pcbnew.FromMM(.35)
        for item in self.overlappings:
            if type(item) is pcbnew.PCB_TRACK and item.GetNetCode() != netcode:
                a,b = item.GetStart(),item.GetEnd()
                capsules.append(((a.x,a.y),(b.x,b.y),
                                 radius+self.clearance+margin+item.GetWidth()/2))
            elif isinstance(item,pcbnew.PCB_VIA) and item.GetNetCode() == netcode:
                p = item.GetPosition()
                capsules.append(((p.x,p.y),(p.x,p.y), settings["drill"]/2 +
                                 self.clearance+item.GetDrillValue()/2+pcbnew.FromMM(.5)))
            elif type(item) is pcbnew.PAD or isinstance(item,pcbnew.PCB_VIA):
                if not required_layers.intersection(item.GetLayerSet().Seq()):
                    continue
                box = item.GetBoundingBox()
                boxes.append((box.GetLeft()-radius-margin, box.GetTop()-radius-margin,
                              box.GetRight()+radius+margin, box.GetBottom()+radius+margin))
        sections = {}
        def blocked(axis,value):
            key = axis,value
            if key not in sections:
                intervals = [capsule_section(a,b,r,axis,value) for a,b,r in capsules]
                intervals.extend((box[axis],box[axis+2]) for box in boxes
                                 if box[1-axis] <= value <= box[3-axis])
                sections[key] = [interval for interval in intervals if interval is not None]
            return sections[key]
        for via in self.board.GetTracks():
            if not isinstance(via, pcbnew.PCB_VIA) or via.GetNetCode() != netcode:
                continue
            spanned = required_layers.intersection(via.GetLayerSet().Seq())
            point = (via.GetPosition().x, via.GetPosition().y)
            # Every same-net via excludes nearby refill positions. Electrical
            # island coverage is a separate property, never an index filter.
            connects = (not self.m_chkAllCopperLayers.GetValue()
                        or required_layers.issubset(spanned)) and self.HasFilledCopperAt(
                            via.GetPosition(), sorted(spanned), netcode, _via_width(via) / 2)
            touched = [i for i, region in enumerate(self.fill_regions)
                       if connects and region.layer in spanned
                       and region.fits(point, _via_width(via, region.layer) / 2)]
            index.add(point, touched)
        dialog = wx.ProgressDialog(_("Refill islands and gaps"),
            _("Searching for additional via positions..."), parent=self,
            style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME)
        try:
            def progress(added, examined):
                keep_going, _skip = dialog.Pulse(_("Additional vias: {vias}\nPositions checked: {checked}").format(vias=added, checked=examined))
                return keep_going
            return refill(self.fill_regions, index, origin, settings["pitch"],
                          settings["diameter"], settings["minimum"], settings["maximum"],
                          self._place_via, stagger=stagger, progress=progress,
                          blocked=blocked)
        finally:
            dialog.Destroy()

    def FillupArea(self):
        """Fills selected area with vias."""

        settings = self.fill_settings
        viasize = settings["diameter"]
        step_x, step_y = settings["pitch"]
        offset_x, offset_y = settings["offset"]
        clearance = settings["clearance"]
        fill_style = self._get_fill_style()
        self.randomize = fill_style == "Randomize"
        stagger = fill_style == "Stagger"
        self.clearance = clearance
        bbox = self.area.GetBoundingBox()
        top = bbox.GetTop()
        bottom = bbox.GetBottom()
        right = bbox.GetRight()
        left = bbox.GetLeft()
        # commit = pcbnew.COMMIT()
        viacount = 0
        
        # Bug fix 1: Shrink effective bounding box by via radius on all sides
        via_r = viasize // 2
        eff_left = left + via_r
        eff_right = right - via_r
        eff_top = top + via_r
        eff_bottom = bottom - via_r
        
        # Bug fix 2: Correct grid start point calculation
        # Find first grid point that is >= eff_left
        faza_x = (eff_left + offset_x) % step_x
        x_start = eff_left if faza_x == 0 else eff_left + (step_x - faza_x)
        
        # Find first grid point that is >= eff_top
        faza_y = (eff_top + offset_y) % step_y
        y_start = eff_top if faza_y == 0 else eff_top + (step_y - faza_y)

        # Cycle through area bounding box checking and implanting vias
        # Refactored to row-major for stagger support
        y = y_start
        row_index = 0
        while y <= eff_bottom:
            # Calculate X offset for this row if staggering is enabled
            row_x_offset = 0
            if stagger and (row_index % 2 == 1):
                # Offset every other row by half the horizontal spacing
                row_x_offset = step_x // 2
            
            x = x_start + row_x_offset
            while x <= eff_right:
                if self.randomize:
                    xp = x + random.uniform(-1, 1) * step_x / 5
                    yp = y + random.uniform(-1, 1) * step_y / 5
                else:
                    xp = x
                    yp = y

                if self._place_via((xp, yp)):
                    viacount += 1
                x += step_x
            y += step_y
            row_index += 1

        if settings["adaptive"]:
            result = self._refill((x_start, y_start), stagger)
            message = _("Grid vias: {grid}\nAdditional vias: {extra}\nUnserved copper islands (per layer): {unserved}").format(
                grid=viacount, extra=result.added, unserved=result.unserved)
            if result.limited:
                message += "\n" + _("Search limit reached. Partial results kept; some areas may remain unfilled.")
            if result.cancelled:
                message += "\n" + _("Refill stopped. Vias already placed have been kept.")
            wx.MessageBox(message)
        elif viacount > 0:
            wx.MessageBox(_("Implanted: %d vias!") % viacount)
        else:
            wx.MessageBox(_("No vias implanted!"))
        pcbnew.Refresh()

    def onProcessAction(self, event):
        """Manage main button (Ok) click event."""
        try:
            self._read_fill_settings()
        except (ValueError, OverflowError):
            wx.MessageBox(_("Enter positive spacing and via sizes, drill smaller than diameter, non-negative clearance, and distance limits with 0 < minimum <= 100 <= maximum."))
            return
        if self.fill_settings["adaptive"]:
            try:
                self.fill_regions = self._filled_regions()
            except (AttributeError, TypeError, RuntimeError):
                wx.MessageBox(_("This KiCad version cannot read filled copper polygons. Disable refill to use the regular grid."))
                return
            if not self.fill_regions:
                wx.MessageBox(_("Fill the selected copper zone before using refill."))
                return
        zone_name = self.area.GetZoneName()
        if zone_name == "":
            for i in range(1000):
                candidate_name = f"stitch_zone_{i}"
                if candidate_name not in self.config.keys():
                    zone_name = candidate_name
                    break
            else:
                wx.LogError(
                    "Tried 1000 different names and all were taken. Please give a name to the zone."
                )
                self.Destroy()
                return
            self.area.SetZoneName(zone_name)

        # Keep the group name synchronized with the final zone name
        self.viagroupname = __viagroupname_base__ + zone_name

        config = {
            "HSpacing": self.m_txtHSpacing.GetValue(),
            "VSpacing": self.m_txtVSpacing.GetValue(),
            "HOffset": self.m_txtHOffset.GetValue(),
            "VOffset": self.m_txtVOffset.GetValue(),
            "Clearance": self.m_txtClearance.GetValue(),
            "FillStyle": self._get_fill_style(),
            "RequireAllCopperLayers": self.m_chkAllCopperLayers.GetValue(),
            "AdaptiveFill": self.m_chkAdaptiveFill.GetValue(),
            "MinSpacingPercent": self.m_txtMinSpacing.GetValue(),
            "MaxSpacingPercent": self.m_txtMaxSpacing.GetValue(),
        }

        if self.config_textbox is None:
            self.config = {__plugin_config_key__: __version__}
            title_block = pcbnew.PCB_TEXT(self.board)
            title_block.SetLayer(self.config_layer)

            if hasattr(pcbnew, "GR_TEXT_HJUSTIFY_LEFT"):
                title_block.SetHorizJustify(pcbnew.GR_TEXT_HJUSTIFY_LEFT)
            else:
                if hasattr(pcbnew, "GR_TEXT_H_ALIGN_LEFT"):
                    title_block.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)

            if hasattr(pcbnew, "GR_TEXT_VJUSTIFY_TOP"):
                title_block.SetVertJustify(pcbnew.GR_TEXT_VJUSTIFY_TOP)
            else:
                if hasattr(pcbnew, "GR_TEXT_V_ALIGN_TOP"):
                    title_block.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_TOP)

            title_block.SetVisible(False)
            self.config_textbox = title_block
            self.board.Add(title_block)
        self.config[zone_name] = config

        self.config_textbox.SetText(json.dumps(self.config, indent=2))

        # Get overlapping items
        self.GetOverlappingItems()

        # Search trough groups
        for group in self.board.Groups():
            if group.GetName() == self.viagroupname:
                self.pcb_group = group

        if self.pcb_group is None:
            self.pcb_group = pcbnew.PCB_GROUP(None)
            self.pcb_group.SetName(self.viagroupname)
            self.board.Add(self.pcb_group)

        self.FillupArea()
        self.Destroy()

    def onClearAction(self, event):
        """Manage clear vias button (Clear) click event."""

        self.ClearArea()
        self.Destroy()

    def onCloseWindow(self, event):
        """Manage Close button click event."""

        self.Destroy()

    def GetStandardLayerName(self, layerid):
        if hasattr(pcbnew, "BOARD_GetStandardLayerName"):
            layer_name = pcbnew.BOARD_GetStandardLayerName(layerid)
        else:
            layer_name = self.board.GetStandardLayerName(layerid)

        return layer_name

    def getConfigLayer(self):
        self.config_layer = 0
        user_layer = 0
        for i in range(
            pcbnew.PCBNEW_LAYER_ID_START,
            pcbnew.PCBNEW_LAYER_ID_START + pcbnew.PCB_LAYER_ID_COUNT,
        ):
            if __plugin_config_layer_name__ == self.GetStandardLayerName(i):
                self.config_layer = i
                break
            if "User.9" == self.GetStandardLayerName(i):
                user_layer = i
        else:
            self.config_layer = user_layer
            self.board.SetLayerName(self.config_layer, __plugin_config_layer_name__)


def InitViaStitcherDialog(board):
    """Initalize dialog."""

    dlg = ViaStitcherDialog(board)
    if dlg.initialized:
        dlg.Show(True)
    return dlg


class aVector:
    def __init__(self, point: [pcbnew.wxPoint, list]):
        if isinstance(point, pcbnew.wxPoint):
            self.x = float(point.x)
            self.y = float(point.y)
        elif isinstance(point, list):
            self.x = point[0]
            self.y = point[1]

    def __sub__(self, other: pcbnew.wxPoint):
        return aVector([self.x - float(other.x), self.y - float(other.y)])

    def __mul__(self, other):
        return aVector([self.x * float(other), self.y * float(other)])

    def __add__(self, other):
        return aVector([self.x + float(other.x), self.y + float(other.y)])

    def __truediv__(self, other):
        return aVector([self.x / other, self.y / other])

    @staticmethod
    def norm(vector):
        return sqrt(pow(vector.x, 2) + pow(vector.y, 2))

    @staticmethod
    def dot(vector1, vector2):
        return vector1.x * vector2.x + vector1.y * vector2.y


# Given a line with coordinates 'start' and 'end' and the
# coordinates of a point 'point' the proc returns the shortest
# distance from pnt to the line and the coordinates of the
# nearest point on the line.
#
# 1  Convert the line segment to a vector ('line_vec').
# 2  Create a vector connecting start to pnt ('pnt_vec').
# 3  Find the length of the line vector ('line_len').
# 4  Convert line_vec to a unit vector ('line_unitvec').
# 5  Scale pnt_vec by line_len ('pnt_vec_scaled').
# 6  Get the dot product of line_unitvec and pnt_vec_scaled ('t').
# 7  Ensure t is in the range 0 to 1.
# 8  Use t to get the nearest location on the line to the end
#    of vector pnt_vec_scaled ('nearest').
# 9  Calculate the distance from nearest to pnt_vec_scaled.
# 10 Translate nearest back to the start/end line.
# Malcolm Kesson 16 Dec 2012


def pnt2line(point: pcbnew.wxPoint, start: pcbnew.wxPoint, end: pcbnew.wxPoint):
    pnt = vector([point.x, point.y])
    strt = vector([start.x, start.y])
    nd = vector([end.x, end.y])
    line_vec = nd - strt
    pnt_vec = pnt - strt
    line_len = norm(line_vec)

    # --- ANTI CRASH ---
    if line_len < 0.0001:
        dist = norm(pnt_vec)
        return dist, strt
    # --- END PATCH ---

    line_unitvec = line_vec / line_len
    pnt_vec_scaled = pnt_vec / line_len
    t = dot(line_unitvec, pnt_vec_scaled)
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    nearest = line_vec * t
    dist = norm(pnt_vec - nearest)
    nearest = nearest + strt
    return dist, nearest


norm = aVector.norm
vector = aVector
dot = aVector.dot
if numpy_available:
    norm = np.linalg.norm
    vector = np.array
    dot = np.dot
