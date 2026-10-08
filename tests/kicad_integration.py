"""Run with KiCad's Python. Creates only synthetic boards in the output directory.

Usage: <kicad-python> tests/kicad_integration.py /tmp/viastitcher-check
Then run kicad-cli pcb drc --refill-zones --format json on before/after boards.
"""
import importlib
import json
from pathlib import Path
import random
import sys
import subprocess
import tempfile
import os
import types
from unittest.mock import patch

import pcbnew
import wx

ROOT = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('viastitcher_test_package')
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
module = importlib.import_module(pkg.__name__ + '.viastitcher_dialog')
Dialog = module.ViaStitcherDialog


def mm(value):
    return pcbnew.FromMM(value)


def point(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def layers(*ids):
    result = pcbnew.LSET()
    for layer in ids:
        result.AddLayer(layer)
    return result


def board_fixture():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    gnd = pcbnew.NETINFO_ITEM(board, 'GND')
    signal = pcbnew.NETINFO_ITEM(board, 'SIGNAL')
    board.Add(gnd)
    board.Add(signal)
    for start, end in [((0,0),(36,0)),((36,0),(36,25)),((36,25),(0,25)),((0,25),(0,0))]:
        edge = pcbnew.PCB_SHAPE(board)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetStart(point(*start)); edge.SetEnd(point(*end))
        edge.SetLayer(pcbnew.Edge_Cuts); edge.SetWidth(mm(.05))
        board.Add(edge)
    zone = pcbnew.ZONE(board)
    zone.SetNet(gnd)
    zone.SetZoneName('adaptive_fixture')
    zone.SetAssignedPriority(1)
    zone.SetLayerSet(layers(pcbnew.F_Cu, pcbnew.B_Cu))
    zone.SetLocalClearance(mm(.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    # One outline with a narrow bridge, severed by a copper keepout below.
    corners = [(2,2),(26,2),(26,10.8),(30.4,10.8),(30.4,10.4),
               (31.6,10.4),(31.6,11.6),(30.4,11.6),(30.4,11.2),
               (26,11.2),(26,22),(2,22)]
    idx = zone.Outline().NewOutline()
    for x,y in corners:
        zone.Outline().Append(mm(x),mm(y),idx)
    board.Add(zone)
    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    keepout.SetLayerSet(layers(pcbnew.F_Cu, pcbnew.B_Cu))
    keepout.SetDoNotAllowZoneFills(True)
    idx = keepout.Outline().NewOutline()
    for x,y in [(26,10),(30.4,10),(30.4,12),(26,12)]:
        keepout.Outline().Append(mm(x),mm(y),idx)
    board.Add(keepout)
    # A foreign-net SMD pad blocks a nominal grid point and creates a copper hole.
    footprint = pcbnew.FOOTPRINT(board)
    footprint.SetReference('J1')
    footprint.SetPosition(point(12,12))
    pad = pcbnew.PAD(footprint)
    pad.SetNumber('1'); pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT, pcbnew.F_Cu)
    pad.SetSize(point(.6,.6)); pad.SetLayerSet(layers(pcbnew.F_Cu))
    pad.SetPosition(point(12,12)); pad.SetNet(signal)
    footprint.Add(pad); board.Add(footprint)
    # A backing plane connects the islands through another layer, as on a real
    # stitching board. Otherwise adding a via to floating copper necessarily
    # exposes a new unconnected-net item, unrelated to placement clearance.
    plane = pcbnew.ZONE(board)
    plane.SetLayer(pcbnew.B_Cu)
    plane.SetNet(gnd)
    plane.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    plane.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    plane.SetLocalClearance(mm(.2))
    idx = plane.Outline().NewOutline()
    for x,y in [(1,1),(35,1),(35,24),(1,24)]:
        plane.Outline().Append(mm(x),mm(y),idx)
    board.Add(plane)
    ground_fp = pcbnew.FOOTPRINT(board)
    ground_fp.SetReference('J2'); ground_fp.SetPosition(point(3,3))
    ground_pad = pcbnew.PAD(ground_fp)
    ground_pad.SetNumber('1'); ground_pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    ground_pad.SetShape(pcbnew.PAD_SHAPE_RECT, pcbnew.B_Cu)
    ground_pad.SetSize(point(.6,.6)); ground_pad.SetLayerSet(layers(pcbnew.B_Cu))
    ground_pad.SetPosition(point(3,3)); ground_pad.SetNet(gnd)
    ground_fp.Add(ground_pad); board.Add(ground_fp)
    board.BuildConnectivity()
    # The CLI initializes KiCad's project/rule engine before filling, unlike
    # ZONE_FILLER on a freshly constructed BOARD in standalone Python.
    cli = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'fixture.kicad_pcb'
        pcbnew.SaveBoard(str(path), board)
        subprocess.run([cli, 'pcb', 'drc', '--refill-zones', '--save-board',
                        '--format', 'json', '-o', str(Path(directory)/'drc.json'), str(path)],
                       check=True, stdout=subprocess.DEVNULL)
        board = pcbnew.LoadBoard(str(path))
    return board, next(z for z in board.Zones() if z.GetZoneName() == 'adaptive_fixture')


class Control:
    def __init__(self, value): self.value = value
    def GetValue(self): return self.value
    def GetStringSelection(self): return self.value
    def GetSelection(self): return self.value
    def IsChecked(self): return self.value
    def SetValue(self, value): self.value = value


class Harness:
    # Exercise actual plugin methods with real KiCad geometry, without opening
    # modal message/progress dialogs during automated tests.
    pass

for name in dir(Dialog):
    if name.startswith('_') and name not in ('_read_fill_settings','_filled_regions','_point','_place_via','_get_fill_style','_refill','_copper_layers'):
        continue
    value = getattr(Dialog,name)
    if callable(value):
        setattr(Harness,name,staticmethod(value) if name == '_point' else value)


def harness(board, zone, adaptive=False, style=0):
    h = Harness()
    h.board, h.area, h.net = board, zone, 'GND'
    h.FromUserUnit = pcbnew.FromMM
    h.board_edges = list(board.GetDrawings())
    h.viagroupname = 'VIA_STITCHING_GROUPadaptive_fixture'
    h.pcb_group = pcbnew.PCB_GROUP(board)
    h.pcb_group.SetName(h.viagroupname); board.Add(h.pcb_group)
    h.config = {}; h.config_textbox = None; h.config_layer = pcbnew.User_9
    h.Destroy = lambda: None
    controls = dict(m_txtViaSize='.6',m_txtViaDrillSize='.3',m_txtHSpacing='4',m_txtVSpacing='4',
                    m_txtHOffset='0',m_txtVOffset='0',m_txtClearance='0',m_cbNet='GND',
                    m_chkAllCopperLayers=True,m_cbFillStyle=style,m_chkAdaptiveFill=adaptive,
                    m_txtMinSpacing='80',m_txtMaxSpacing='150',m_chkClearOwn=True)
    for name,value in controls.items(): setattr(h,name,Control(value))
    h._read_fill_settings()
    h.clearance = h.fill_settings['clearance']
    h.fill_regions = h._filled_regions()
    h.GetOverlappingItems()
    return h


class Progress:
    def __init__(self,*args,**kwargs): pass
    def Pulse(self,*args): return True,False
    def Destroy(self): pass


def vias(board):
    return [v for v in board.GetTracks() if isinstance(v,pcbnew.PCB_VIA)]


def spacing_snapshot(board):
    return {v.m_Uuid.AsString(): (v.GetPosition().x, v.GetPosition().y)
            for v in vias(board) if v.GetNetname() == 'GND'}


def assert_refill_spacing(board, before, pitch, minimum=.8):
    import math
    points = list(before.values())
    for uid, p in spacing_snapshot(board).items():
        if uid in before:
            continue
        for q in points:
            distance = math.hypot((p[0]-q[0])/pitch[0], (p[1]-q[1])/pitch[1])
            assert distance >= minimum, (p,q,distance,minimum)
        points.append(p)


def run(output):
    output.mkdir(parents=True,exist_ok=True)
    results = {}
    for style in range(3):
        board, zone = board_fixture()
        h = harness(board,zone,style=style)
        assert len(h.fill_regions) == 4, len(h.fill_regions)
        random.seed(42)
        h.FillupArea()
        first = len(vias(board))
        before = spacing_snapshot(board)
        assert first > 0
        assert not any(v.GetPosition().x > mm(30) for v in vias(board))
        pcbnew.SaveBoard(str(output / ('before_%d.kicad_pcb' % style)),board)
        h.fill_settings['adaptive'] = True
        # The nominal origin for this fixture is (4 mm, 4 mm).
        result = h._refill((mm(4),mm(4)), style == 1)
        assert_refill_spacing(board, before, (mm(4),mm(4)))
        assert result.added > 0, result
        assert result.unserved == 0, result
        assert any(v.GetPosition().x > mm(30) for v in vias(board))
        assert len(h.pcb_group.GetItems()) == first + result.added
        pcbnew.SaveBoard(str(output / ('after_%d.kicad_pcb' % style)),board)
        assert not h._place_via((vias(board)[0].GetPosition().x,vias(board)[0].GetPosition().y))
        results[str(style)] = dict(grid=first,additional=result.added,unserved=result.unserved)
        # Re-running the adaptive pass does not duplicate vias.
        again = h._refill((mm(4),mm(4)), style == 1)
        assert again.added == 0, again
        h.ClearArea()
        assert len(vias(board)) == 0

    # A four-layer board with GND only on F/B must accept two-layer mode,
    # reject all-layer mode, and never accept a single copper connection.
    board,zone = board_fixture(); board.SetCopperLayerCount(4)
    h = harness(board,zone)
    assert not h._place_via((mm(4),mm(4)))
    strict_refill = h._refill((mm(4),mm(4)),False)
    assert strict_refill.added == 0 and not vias(board)
    h.m_chkAllCopperLayers.SetValue(False)
    assert h._place_via((mm(4),mm(4)))
    # The main placement routine intentionally keeps its existing collision
    # rules: this 1 mm pair is closer than the refill minimum of 3.2 mm.
    assert h._place_via((mm(5),mm(4)))
    assert not h.HasFilledCopperAt(point(4,4),[pcbnew.F_Cu],board.GetNetcodeFromNetname('GND'),mm(.3))
    assert not h._place_via((mm(12),mm(12)))
    h.FillupArea()
    two_layer_refill = h._refill((mm(4),mm(4)),False)
    assert two_layer_refill.added > 0 and two_layer_refill.unserved == 0
    results['copper_modes'] = 'Two-layer acceptance, all-layer rejection, single-layer and obstacle rejection'

    # Two foreign tracks leave only a 25 um placement window under the shared
    # collision rules. Neither the nominal 1.5 mm grid nor coarse offsets hit
    # it. Both copper planes are continuous: this is a gap, not a new island.
    board, zone = board_fixture(); board.SetCopperLayerCount(4)
    for x in (10.3, 11.775):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(point(x,3)); track.SetEnd(point(x,22))
        track.SetWidth(mm(.15)); track.SetLayer(pcbnew.In1_Cu)
        track.SetNetCode(board.GetNetcodeFromNetname('SIGNAL')); board.Add(track)
    h = harness(board, zone)
    h.m_chkAllCopperLayers.SetValue(False)
    h.m_txtHSpacing.SetValue('1.5'); h.m_txtVSpacing.SetValue('1.5')
    h._read_fill_settings(); h.FillupArea()
    def corridor_vias():
        return [v for v in vias(board) if mm(11.025) < v.GetPosition().x < mm(11.05)
                and mm(5) < v.GetPosition().y < mm(20)]
    assert not corridor_vias()
    first = len(vias(board))
    before = spacing_snapshot(board)
    pcbnew.SaveBoard(str(output/'before_corridor.kicad_pcb'), board)
    result = h._refill((0,0), False)
    assert_refill_spacing(board, before, (mm(1.5),mm(1.5)))
    assert len(corridor_vias()) >= 8, (result, len(corridor_vias()))
    assert len(h.pcb_group.GetItems()) == first + result.added
    pcbnew.SaveBoard(str(output/'after_corridor.kicad_pcb'), board)
    results['corridor'] = dict(grid=first, additional=result.added,
                               corridor_vias=len(corridor_vias()))
    h.ClearArea(); assert not vias(board)

    # Invalid settings must not name an unnamed zone, add a group, or save config.
    board,zone = board_fixture(); h = harness(board,zone)
    zone.SetZoneName('')
    h.m_txtHSpacing.SetValue('0')
    h.onProcessAction(None)
    assert zone.GetZoneName() == '' and h.config_textbox is None and not vias(board)

    # Only same-net vias spanning the selected layer set count as coverage.
    h.m_txtHSpacing.SetValue('4'); h._read_fill_settings()
    board.SetCopperLayerCount(4)
    h.m_chkAllCopperLayers.SetValue(False)
    for net,top,bottom,xy in [('GND',pcbnew.F_Cu,pcbnew.B_Cu,(31,11)),
                              ('SIGNAL',pcbnew.F_Cu,pcbnew.B_Cu,(8,8)),
                              ('GND',pcbnew.F_Cu,pcbnew.In1_Cu,(20,20))]:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(point(*xy)); via.SetWidth(mm(.6)); via.SetDrill(mm(.3))
        via.SetNetCode(board.GetNetcodeFromNetname(net))
        if bottom == pcbnew.In1_Cu:
            via.SetViaType(pcbnew.VIATYPE_BLIND)
        via.SetLayerPair(top,bottom)
        board.Add(via)
    with patch.object(module,'refill') as inspect:
        h._refill((mm(4),mm(4)),False)
        index = inspect.call_args.args[1]
        assert sum(len(bucket) for bucket in index.buckets.values()) == 2
        assert len(index.covered) == 2
    before = spacing_snapshot(board)
    h._refill((mm(4),mm(4)),False)
    assert_refill_spacing(board,before,(mm(4),mm(4)))
    results['existing_vias'] = 'All same-net vias block spacing; only connected vias supply islands'

    # Persist and reload new fields through the real process path.
    board,zone = board_fixture(); h = harness(board,zone,adaptive=True)
    h.onProcessAction(None)
    saved = json.loads(h.config_textbox.GetText())['adaptive_fixture']
    assert saved['AdaptiveFill'] is True
    assert saved['MinSpacingPercent'] == '80' and saved['MaxSpacingPercent'] == '150'
    results['settings'] = saved
    (output/'summary.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    app = wx.App(False)
    with patch.object(wx,'MessageBox',lambda *a,**k: None), patch.object(wx,'ProgressDialog',Progress), patch.object(pcbnew,'Refresh',lambda: None):
        run(Path(sys.argv[1]))
