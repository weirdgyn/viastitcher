# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

import gettext
_ = gettext.gettext

###########################################################################
## Class viastitcher_gui
###########################################################################

class viastitcher_gui ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = _(u"Via Stitcher"), pos = wx.DefaultPosition, size = wx.Size( -1,-1 ), style = wx.DEFAULT_DIALOG_STYLE )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bMainSizer = wx.BoxSizer( wx.VERTICAL )

		fgSizer1 = wx.FlexGridSizer( 0, 4, 0, 0 )
		fgSizer1.AddGrowableCol( 0 )
		fgSizer1.SetFlexibleDirection( wx.BOTH )
		fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_lblStyle = wx.StaticText( self, wx.ID_ANY, _(u"Style"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblStyle.Wrap( -1 )

		fgSizer1.Add( self.m_lblStyle, 0, wx.ALL|wx.EXPAND, 5 )

		self.m_chkStagger = wx.CheckBox( self, wx.ID_ANY, _(u"Create staggered pattern"), wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_chkStagger, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.m_chkRandomize = wx.CheckBox( self, wx.ID_ANY, _(u"Randomize"), wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_chkRandomize, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.m_lblNetName = wx.StaticText( self, wx.ID_ANY, _(u"Net name"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblNetName.Wrap( -1 )

		fgSizer1.Add( self.m_lblNetName, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5 )

		m_cbNetChoices = []
		self.m_cbNet = wx.ComboBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, m_cbNetChoices, wx.CB_DROPDOWN|wx.CB_READONLY|wx.CB_SORT )
		fgSizer1.Add( self.m_cbNet, 0, wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.m_lblViaParams = wx.StaticText( self, wx.ID_ANY, _(u"Size / drill"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblViaParams.Wrap( -1 )

		fgSizer1.Add( self.m_lblViaParams, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtViaSize = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtViaSize.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtViaSize, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtViaDrillSize = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtViaDrillSize.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtViaDrillSize, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_lblUnit1 = wx.StaticText( self, wx.ID_ANY, _(u"mm"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblUnit1.Wrap( -1 )

		fgSizer1.Add( self.m_lblUnit1, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_lblSpacing = wx.StaticText( self, wx.ID_ANY, _(u"Spacing (V/H)"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblSpacing.Wrap( -1 )

		fgSizer1.Add( self.m_lblSpacing, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtVSpacing = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtVSpacing.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtVSpacing, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtHSpacing = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtHSpacing.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtHSpacing, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_lblUnit2 = wx.StaticText( self, wx.ID_ANY, _(u"mm"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblUnit2.Wrap( -1 )

		fgSizer1.Add( self.m_lblUnit2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_lblOffset = wx.StaticText( self, wx.ID_ANY, _(u"Offset (V/H)"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblOffset.Wrap( -1 )

		fgSizer1.Add( self.m_lblOffset, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtVOffset = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtVOffset.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtVOffset, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtHOffset = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtHOffset.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtHOffset, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_lblUnit3 = wx.StaticText( self, wx.ID_ANY, _(u"mm"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblUnit3.Wrap( -1 )

		fgSizer1.Add( self.m_lblUnit3, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_lblClearance = wx.StaticText( self, wx.ID_ANY, _(u"Clearance"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblClearance.Wrap( -1 )

		fgSizer1.Add( self.m_lblClearance, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )

		self.m_txtClearance = wx.TextCtrl( self, wx.ID_ANY, _(u"0"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtClearance.SetMinSize( wx.Size( 120,-1 ) )

		fgSizer1.Add( self.m_txtClearance, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.m_lblUnit4 = wx.StaticText( self, wx.ID_ANY, _(u"mm"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_lblUnit4.Wrap( -1 )

		fgSizer1.Add( self.m_lblUnit4, 0, wx.ALL|wx.EXPAND, 5 )


		bMainSizer.Add( fgSizer1, 1, wx.EXPAND, 5 )

		self.m_sline1 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		bMainSizer.Add( self.m_sline1, 0, wx.EXPAND |wx.ALL, 5 )

		bSizer1 = wx.BoxSizer( wx.VERTICAL )

		self.m_chkOnlyFilledCopper = wx.CheckBox( self, wx.ID_ANY, _(u"Only place vias that connect filled copper of the selected net on multiple layers"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_chkOnlyFilledCopper.SetValue(True)
		bSizer1.Add( self.m_chkOnlyFilledCopper, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND|wx.LEFT, 5 )

		self.m_chkClearOwn = wx.CheckBox( self, wx.ID_ANY, _(u"Clear only plugin placed vias"), wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_chkClearOwn.SetValue(True)
		bSizer1.Add( self.m_chkClearOwn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND|wx.LEFT, 5 )


		bMainSizer.Add( bSizer1, 0, wx.EXPAND, 5 )

		self.m_sline2 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		bMainSizer.Add( self.m_sline2, 0, wx.EXPAND |wx.ALL, 5 )

		bSizer2 = wx.BoxSizer( wx.HORIZONTAL )

		self.m_btnOk = wx.Button( self, wx.ID_ANY, _(u"&Ok"), wx.DefaultPosition, wx.DefaultSize, 0 )

		self.m_btnOk.SetDefault()
		bSizer2.Add( self.m_btnOk, 0, wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_btnCancel = wx.Button( self, wx.ID_ANY, _(u"&Cancel"), wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer2.Add( self.m_btnCancel, 0, wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_btnClear = wx.Button( self, wx.ID_ANY, _(u"C&lear"), wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer2.Add( self.m_btnClear, 0, wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


		bMainSizer.Add( bSizer2, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5 )


		self.SetSizer( bMainSizer )
		self.Layout()
		bMainSizer.Fit( self )

		self.Centre( wx.BOTH )

	def __del__( self ):
		pass


