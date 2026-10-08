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

## Localization

ViaStitcher follows KiCad's active interface language and currently includes English and Italian catalogs. English source strings are the fallback when no matching catalog is available. Set `VIASTITCHER_LANGUAGE` (for example, to `it_IT`) to override language detection while testing.

After editing a `.po` file, compile the runtime `.mo` catalogs before committing:

```text
python locale_setup.py
```

`viastitcher.fbp` is the source of truth for the dialog layout. It has wxFormBuilder internationalization enabled; therefore regenerated `viastitcher_gui.py` files deliberately use `gettext.gettext`. Do not edit the generated file to change its translation import: `localization.py` installs the selected ViaStitcher catalog as gettext's default domain when the plugin loads.

## How it works

Select a filled copper zone and start **Tools → External Plugins → ViaStitcher**, or use the ![ViaStitcher icon](viastitcher.png?raw=true) toolbar button. The following dialog opens:

![ViaStitcher dialog](pictures/viastitcher_dialog.png?raw=true "ViaStitcher dialog")

The zone net is selected automatically, but another net can be chosen when needed. The dialog provides:

- via diameter and drill diameter, initialized from the board settings;
- vertical and horizontal spacing;
- vertical and horizontal grid offsets;
- clearance from the zone boundary and board edges (`0` disables the additional clearance check);
- optional randomized placement;
- **Require copper connection on all layers (off: at least two)**.

The copper-connection checkbox is **off by default**: a via must have its full annular area over the selected net on at least two copper layers. Enable it to require this on every copper layer traversed by the through via. The setting is saved per zone as `RequireAllCopperLayers`. Legacy `OnlyFilledCopper=true` settings migrate to the stricter all-layer mode; unchecked legacy settings now require at least two connected layers instead of allowing single-layer placement. The checkbox never disables collision checks.

Generated vias are marked as free vias when supported by the KiCad API. This prevents KiCad's automatic via-net update from changing their assigned net when several filled zones overlap.

Press **Ok** to generate the vias. Always run KiCad's Design Rules Checker after stitching.
If everything goes fine you'll get something like this:

![ViaStitcher result](pictures/viastitcher_result.png?raw=true "ViaStitcher result")

ViaStitcher checks pads, tracks, vias, footprint zones, board edges, and items belonging to other nets before placing each via. Complex boards may still expose cases not covered by the plugin, so DRC verification remains essential.

Use **Clear** to remove matching vias from the selected zone. With **Clear only plugin placed vias** enabled, only vias belonging to that zone's ViaStitcher group are removed. Disable it to remove any via matching the selected net, size, and drill values inside the zone.

## Optional island and gap refill

Enable **Refill islands and gaps** to run a second pass after the selected grid
style (Standard, Stagger, or Randomize). It uses the selected zone's actual
filled copper polygons, including holes and disconnected islands on each layer.
Small islands can receive a via even when no grid point falls inside them.
Every existing via of the selected net blocks its minimum-spacing area,
including manually placed vias and vias without qualifying copper connections.
Only vias satisfying the chosen two-layer or all-layer connection requirement
count toward electrical island coverage. These are separate checks.
Vias on a different island do not count as that island's connection.

**Refill spacing (min/max %)** defaults to **80 / 150**. These percentages apply
to center-to-center distances normalized by the horizontal and vertical grid
spacing: `hypot(dx / HSpacing, dy / VSpacing)`. Thus a horizontal 4 mm grid aims
for 4 mm neighbors, allowing 3.2–6 mm in that direction. Limits must satisfy
`0 < minimum <= 100 <= maximum`. They affect only additional vias; existing and
first-pass vias are not moved. The option and both limits are saved per zone;
older configurations default to refill disabled.

Refill tries nominal grid sites first, then computes the centers of free
horizontal and vertical intervals between obstacles. Track widths, via size,
and the existing collision margins are included before computing these centers.
The perpendicular direction is also checked for pockets offset in both axes.
Regions narrower than the via diameter in either dimension are discarded.
Areas proven entirely covered by via spacing exclusions are skipped; partially
free areas remain candidates. New vias update the spacing index immediately.

There is no fixed wall-clock or total-candidate cutoff. The finite search ends
when a complete traversal adds no more vias; each successful placement completes
one cell. The progress dialog remains cancellable. No increasingly fine search
mesh is generated. Between valid geometric candidates, spacing near 100% of the
requested pitch is preferred over packing at the minimum percentage.

Minimum spacing is mandatory for every additional via, relative to **all**
existing same-net vias and all previously added refill vias. The main grid pass
retains its original collision rules and is not constrained by this percentage.
The maximum is the preferred reach when extending an existing pattern. If that
cannot reach an empty pocket, the search may seed that pocket without a nearby
neighbor. Such seeds still obey minimum spacing and physical placement checks.

This is a geometric placement heuristic, not an exhaustive search or a guarantee
of uniform density. Narrow or obstructed copper may remain unserved; pad bounding
boxes conservatively guide the search, so irregular pad corners may be missed. A progress
dialog allows stopping the refill; vias already placed remain in the plugin's
usual group and can be removed with **Clear only plugin placed vias**. The final
message separates grid and additional vias and counts unserved islands per
layer (the same XY island on two layers counts twice).

Both passes check newly added vias as well as pre-existing board objects.
These are the plugin's existing geometric checks, not KiCad's complete custom
rule engine. Run KiCad DRC after stitching, including a zone refill. On older
KiCad versions without access to filled polygon geometry, disable refill to
continue using the regular grid.

## Tests

Run the geometry tests without KiCad:

```sh
python3 -m unittest discover -s tests -v
```

With KiCad 10's Python (including `pcbnew` and `wx`) and a desktop session:

```sh
export KICAD_CLI=/path/to/kicad-cli
/path/to/kicad-python tests/kicad_integration.py /tmp/viastitcher-check
python3 tests/check_drc.py /tmp/viastitcher-check
/path/to/kicad-python tests/kicad_gui.py
```

The integration script builds synthetic two-layer boards with a blocked grid
site, disconnected copper, and a backing plane. It checks all three styles,
repeat runs, saved settings, validation, and removal of both passes. The DRC
comparison rejects new violations and additional unconnected items. Native wx
tests check control bounds, overlap, toggling, and loading old/new settings.
The integration fixtures target KiCad 10; the existing plugin compatibility
fallbacks for earlier versions are retained.

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
- [x] Localization (English and Italian).
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
- [RealHaltewunsch] (https://github.com/RealHaltewunsch)
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
