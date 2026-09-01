# ViaStitcher

Via stitching action plugin for KiCad 6.0 and newer.

Fill a selected copper area with a pattern of vias.

## When to use this tool

ViaStitcher fills a selected copper zone with a configurable grid of vias. It can be used for ground stitching, shielding, thermal conduction, and current sharing between copper layers.

The plugin works from an existing filled copper zone. Create and fill the zone, select it in PCB Editor, and then start ViaStitcher.

## Install

Install ViaStitcher as a user action plugin in the scripting directory for your KiCad version. On Windows, the usual location is:

```text
C:\Users\<user>\Documents\KiCad\<version>\scripting\plugins\viastitcher
```

Copy the complete repository contents into that directory and restart KiCad. The plugin should appear under **Tools → External Plugins → ViaStitcher**.

## Releases

Release packages for KiCad's Plugin and Content Manager are built automatically when a four-part release tag is pushed. Git tags cannot contain spaces, so use the following format:

```text
Release-x.x.x.x
```

For example, `Release-0.2.0.0` packages PCM version `0.2.0` with version epoch `0`. Before pushing the tag, update `metadata.json` so its version and epoch match. The workflow creates a GitHub release containing the installable PCM ZIP and a `repository-metadata.json` file with the download URL, SHA-256 checksum, download size, and install size required for submission to the official KiCad addon repository. The package uses `viastitcher64x64.png` as its PCM icon while retaining `viastitcher.png` as the PCB Editor toolbar icon.

## How it works

Select a filled copper zone and start **Tools → External Plugins → ViaStitcher**, or use the ![ViaStitcher icon](viastitcher.png?raw=true) toolbar button. The following dialog opens:

![ViaStitcher dialog](pictures/viastitcher_dialog.png?raw=true "ViaStitcher dialog")

The zone net is selected automatically, but another net can be chosen when needed. The dialog provides:

- via diameter and drill diameter, initialized from the board settings;
- vertical and horizontal spacing;
- vertical and horizontal grid offsets;
- clearance from the zone boundary and board edges (`0` disables the additional clearance check);
- optional randomized placement;
- **Only place vias that connect filled copper of the selected net on multiple layers**.

The filled-copper option is enabled by default. When enabled, a via is created only when its complete annular area is over filled copper of the selected net on every relevant layer. When disabled, ViaStitcher uses the selected zone's filled area, matching the earlier placement behavior. This setting is saved independently for each named zone.

Generated vias are marked as free vias when supported by the KiCad API. This prevents KiCad's automatic via-net update from changing their assigned net when several filled zones overlap.

Press **Ok** to generate the vias. Always run KiCad's Design Rules Checker after stitching.
If everything goes fine you'll get something like this:

![ViaStitcher result](pictures/viastitcher_result.png?raw=true "ViaStitcher result")

ViaStitcher checks pads, tracks, vias, footprint zones, board edges, and items belonging to other nets before placing each via. Complex boards may still expose cases not covered by the plugin, so DRC verification remains essential.

Use **Clear** to remove matching vias from the selected zone. With **Clear only plugin placed vias** enabled, only vias belonging to that zone's ViaStitcher group are removed. Disable it to remove any via matching the selected net, size, and drill values inside the zone.

## TODO

Some features still to code:
- [x] Match user units (mm/inches).
- [x] Add clear area function.
- [ ] Draw a better UI (if anyone is willing to contribute please read the following section).
- [x] Collision between new vias and underlying objects: 
   - [x] tracks, 
   - [x] zones,
   - [x] pads,
   - [x] footprint zones,
   - [x] modules,
   - [x] vias.
- [ ] Different fillup patterns/modes (bounding box, centered spiral).
- [x] Avoid placing vias near area edges (define clearance).
- [ ] History management (board commit).
- [ ] Localization.
- [x] Support for multiple zones
- [x] Storage of stitching configuration for each individual zone as JSON string in a user layer.
- [ ] Any request?

## Coding notes

The dialog is maintained in `viastitcher.fbp` using wxFormBuilder 4.2.1. Do not edit `viastitcher_gui.py` independently: update the `.fbp` project and regenerate the Python file so both representations remain synchronized.

After regenerating the GUI, verify that all controls referenced by `viastitcher_dialog.py` are still present. In particular, preserve the V/H offset controls and their 120-pixel minimum field width.

## Relationship to similarly named plugins

This project was originally published as **ViaStitching**. It was renamed to
**ViaStitcher** to avoid confusion with another KiCad plugin using the similar
name **Via-Stitching**. The projects remain independent and differ in user
interface, features, implementation and development direction.

## References

Some useful references that helped me coding this plugin:
1. https://sourceforge.net/projects/wxformbuilder/
2. https://wxpython.org/
3. http://docs.kicad-pcb.org/doxygen-python/namespacepcbnew.html
4. https://forum.kicad.info/c/external-plugins
5. https://github.com/KiCad/kicad-source-mirror/blob/master/Documentation/development/pcbnew-plugins.md
6. https://kicad.mmccoo.com/
7. http://docs.kicad-pcb.org/5.1.4/en/pcbnew/pcbnew.html#kicad_scripting_reference


Tool I got inspired by:
- Altium Via Stitching feature!
- https://github.com/jsreynaud/kicad-action-scripts

## Greetings

Hope someone find my work useful or at least *inspiring* to create something else/better.
Special thanks to everyone that contributed to this project:
- [Giulio Borsoi](https://github.com/giulio-borsoi)
- [danwood76](https://github.com/danwood76)
- [NilujePerchut](https://github.com/NilujePerchut)
- [canislupus11](https://github.com/canislupus11) — staggered/brick-pattern via placement ([#40](https://github.com/weirdgyn/viastitcher/issues/40))

Last but not least, I would like to thank everyone who shared their knowledge of Python and KiCAD with me: Thanks!
#

Live long and prosper!

That's all folks.

By[t]e{s}
 Weirdgyn
