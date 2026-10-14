"""Native keepout regression: <KiCad Python> tests/kicad_keepouts.py OUTPUT.

Uses synthetic boards only. Saves before/after boards for all three placement
patterns with refill, for comparison with kicad-cli pcb drc --refill-zones.
"""
import math
from kicad_integration import *


def rule(board, corners, layer_ids, parent=None):
    z = pcbnew.ZONE(parent or board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(False)
    z.SetLayerSet(layers(*layer_ids))
    outline = z.Outline().NewOutline()
    for x, y in corners:
        z.Outline().Append(mm(x), mm(y), outline)
    (parent or board).Add(z)
    return z


def probe(board, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(point(x, y)); v.SetWidth(mm(.6)); v.SetDrill(mm(.3))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNetCode(board.GetNetcodeFromNetname('GND'))
    return v


def regressions(output):
    board, zone = board_fixture()
    board.SetCopperLayerCount(4)
    z = rule(board, [(6,5),(10,5),(10,9),(6,9)], [pcbnew.In1_Cu])
    # Same name and same net must not hide a rule area; copper fills remain allowed.
    z.SetZoneName(zone.GetZoneName()); z.SetNetCode(zone.GetNetCode())
    h = harness(board, zone); h.m_chkAllCopperLayers.SetValue(False)
    h.board_edges = []
    for xy in [(8,7),(5.8,7),(6,7),(5.9,4.9)]:
        assert h.CheckOverlap(probe(board,*xy)), ('via keepout missed',xy)
    assert not h.CheckOverlap(probe(board,5.69,7)), 'unnecessary exclusion outside radius'
    assert not h.CheckOverlap(probe(board,5.75,4.75)), 'rectangle instead of circle'
    v=probe(board,8,7); v.SetViaType(pcbnew.VIATYPE_BLIND);v.SetLayerPair(pcbnew.In2_Cu,pcbnew.B_Cu)
    assert not h.CheckOverlap(v), 'non-spanned layer blocked'
    z.SetDoNotAllowVias(False)
    assert not h.CheckOverlap(probe(board,8,7)), 'via-allowed area blocked'
    z.SetDoNotAllowVias(True); z.SetIsRuleArea(False)
    assert not h.CheckOverlap(probe(board,8,7)), 'ordinary zone mistaken for keepout'
    z.SetIsRuleArea(True)
    hole=z.Outline().NewHole(0)
    for x,y in [(7,6),(9,6),(9,8),(7,8)]:z.Outline().Append(mm(x),mm(y),0,hole)
    assert not h.CheckOverlap(probe(board,8,7)), 'polygon hole ignored'
    assert h.CheckOverlap(probe(board,7.1,7)), 'copper overlaps hole boundary'
    # Footprint zones are independent of footprint body overlap.
    fp=pcbnew.FOOTPRINT(board);fp.SetPosition(point(100,100));board.Add(fp)
    rule(board,[(14,5),(16,5),(16,9),(14,9)],[pcbnew.F_Cu],fp)
    h.GetOverlappingItems()
    assert h.CheckOverlap(probe(board,15,7)), 'footprint keepout missed'
    assert not h._place_via((mm(15),mm(7)))
    # Both grid and adaptive/gap candidates use the same authoritative check.
    for style in range(3):
        b,z=board_fixture()
        rule(b,[(5,4),(10,4),(10,10),(5,10)],[pcbnew.F_Cu])
        h=harness(b,z,adaptive=True,style=style)
        h.m_txtHSpacing.SetValue('1.5');h.m_txtVSpacing.SetValue('1.5')
        h._read_fill_settings()
        pcbnew.SaveBoard(str(output / ('before_%d.kicad_pcb'%style)),b)
        random.seed(42)
        h.FillupArea()
        assert vias(b)
        positions = [(pcbnew.ToMM(v.GetPosition().x), pcbnew.ToMM(v.GetPosition().y))
                     for v in vias(b)]
        banned = [(x, y) for x, y in positions
                  if math.hypot(max(5-x, 0, x-10), max(4-y, 0, y-10)) < .3]
        assert not banned, ('grid/refill placed inside rectangle', style)
        pcbnew.SaveBoard(str(output / ('after_%d.kicad_pcb'%style)),b)
    print('Keepout regression cases PASS',flush=True)


if __name__ == '__main__':
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    app = wx.App(False)
    with patch.object(wx, 'MessageBox', lambda *a, **k: None), \
         patch.object(wx, 'ProgressDialog', Progress), \
         patch.object(pcbnew, 'Refresh', lambda: None):
        regressions(output)
