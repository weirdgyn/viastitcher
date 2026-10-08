"""Native wx layout and setting migration checks; run with KiCad Python."""
import os
os.environ['WXSUPPRESS_SIZER_FLAGS_CHECK'] = '1'
import json
from unittest.mock import patch
import wx
import pcbnew
from kicad_integration import board_fixture, Dialog

app = wx.App(False)
board, zone = board_fixture()
zone.SetSelected()
with patch.object(pcbnew,'GetBoard',lambda:board), patch.object(pcbnew,'GetUserUnits',lambda:1):
    dialog = Dialog(board)
    assert dialog.initialized
    assert not dialog.m_chkAdaptiveFill.GetValue()
    assert not dialog.m_chkAllCopperLayers.GetValue()
    assert dialog.m_txtMinSpacing.GetValue() == '80'
    assert dialog.m_txtMaxSpacing.GetValue() == '150'
    assert not dialog.m_txtMinSpacing.IsEnabled()
    dialog.m_chkAdaptiveFill.SetValue(True)
    dialog.onAdaptiveFillChanged()
    assert dialog.m_txtMinSpacing.IsEnabled()
    dialog.Layout()
    controls = [dialog.m_chkAdaptiveFill,dialog.m_lblAdaptiveLimits,
                dialog.m_txtMinSpacing,dialog.m_txtMaxSpacing,
                dialog.m_chkAllCopperLayers,dialog.m_chkClearOwn,
                dialog.m_btnOk,dialog.m_btnCancel,dialog.m_btnClear]
    bounds = dialog.GetClientRect()
    for control in controls:
        rect = control.GetRect()
        assert bounds.Contains(rect), (control.GetName(),rect,bounds)
        assert rect.width >= control.GetBestSize().width, (control.GetName(),rect,control.GetBestSize())
    for i, control in enumerate(controls):
        for other in controls[:i]:
            assert not control.GetRect().Intersects(other.GetRect())
    size = tuple(dialog.GetSize())
    dialog.Destroy()
    # Old per-zone settings load defaults without requiring migration.
    config = pcbnew.PCB_TEXT(board)
    config.SetLayer(pcbnew.User_9)
    config.SetText(json.dumps({'ViaStitching':'0.1','adaptive_fixture':{'HSpacing':'3','Randomize':True,'OnlyFilledCopper':True}}))
    board.Add(config)
    old = Dialog(board)
    assert old.initialized
    assert not old.m_chkAdaptiveFill.GetValue()
    assert old.m_txtHSpacing.GetValue() == '3', (old.config, config.GetLayerName(), config.GetText())
    assert old._get_fill_style() == 'Randomize'
    assert old.m_chkAllCopperLayers.GetValue()
    old.Destroy()
    config.SetText(json.dumps({'ViaStitcher':'0.3.4','adaptive_fixture':{
        'AdaptiveFill':True,'RequireAllCopperLayers':False,'MinSpacingPercent':'90','MaxSpacingPercent':'125'}}))
    saved = Dialog(board)
    assert saved.m_chkAdaptiveFill.GetValue()
    assert not saved.m_chkAllCopperLayers.GetValue()
    assert saved.m_txtMinSpacing.IsEnabled()
    assert saved.m_txtMinSpacing.GetValue() == '90'
    assert saved.m_txtMaxSpacing.GetValue() == '125'
    saved.Destroy()
print('GUI layout, toggling, legacy defaults and saved settings: PASS; dialog size',size)
