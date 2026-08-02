# NEGWorkbench

A FreeCAD workbench that integrates **NEG/GL-3** — a historical parametric
geometry programming language — as a native scripted parametric object,
so its output can drive real FreeCAD geometry (e.g. aircraft/helicopter
wing and rotor blade profiles).

Status: **early / pre-alpha**. The GL-3 language interpreter and a small
geometry library are working end-to-end against real GL-3 programs; the
FreeCAD integration (parametric objects, export to native geometry) is an
active work in progress. This is not yet installable as a FreeCAD Addon.

## What is NEG/GL-3?

NEG (*Numerical Etalon Geometry*) is a numerical/parametric geometry
definition language. Its constructional subset, **GL-3**, was used to
describe geometry (typically aerodynamic surface profiles) parametrically,
so that changing input data would recompute the dependent geometry.

> "Etalon" here is used in its metrology sense — a certified reference /
> master standard — reflecting the language's original purpose: defining
> a reference-quality master geometry, similar in spirit to a "master
> model" in aerospace manufacturing.

**Historical context:** NEG/GL-3 originates from work at the former
**LET Kunovice** aircraft manufacturer (Czechoslovakia/Czech Republic),
whose successor is **Aircraft Industries a.s.** This project is an
**independent, from-scratch reimplementation** of the GL-3 constructional
subset as a Python interpreter, written from published/available
documentation and from example `.GL3` programs. It does not include or
derive from Aircraft Industries' original Fortran source code; only the
language's naming conventions (opcodes, procedure names) are carried over
for traceability. Out of scope entirely: GL-3's machining/technology
commands and its CL-2 CNC postprocessor.

## Project layout

```
Init.py                   - App-level entry point (no Gui) - registers
                           gl3fc.gl3_library/gl3_program/gl3_export in
                           sys.modules at FreeCAD startup, regardless of
                           whether the NEG/GL3 workbench was ever
                           activated (needed so opening a saved .FCStd
                           file with GL3Library/GL3Program/GL3Export
                           objects works before first activation - see
                           gl3_wb_paths.py/InitGui.py docstrings)
InitGui.py               - FreeCAD workbench entry point (Gui.Workbench,
                           toolbar/menu registration)
gl3_commands.py           - Gui.Command definitions (currently: create a
                           GL3Library object)
Resources/icons/          - workbench + command icons
gl3/
    gl3_lang.py         - lexer, parser, AST for GL-3
    gl3_interpreter.py  - interpreter (Environment, CALL, I/O channels, ...)
    gl3_ops.py          - operation/command registry, type table
    gl3_analysis.py      - in:/out: parameter direction analysis
    gerlib/             - standalone 2D/3D geometry library (no GL-3/FreeCAD
                          dependency), one file per operation, named after
                          the original GL-3 opcode
    gl3fc/               - FreeCAD integration layer:
        gl3_library.py   - GL3Library: search paths for called subroutines
        gl3_program.py   - GL3Program: FeaturePython object running one
                          top-level GL-3 subroutine, auto-generated in:/out:
                          properties
        gl3_export.py    - GL3Export: converts a GL3Program's composite
                          output into native FreeCAD geometry (Part::Shape)
                          with a real Placement
    examples/            - sample .GL3 programs used as regression tests
docs/
    cs/                  - original Czech design notes (development diary)
```

## Architecture (summary)

- **Two separate modules, one-way data flow:** `GL3Program -> GL3Export ->
  rest of FreeCAD`, never back. Only scalars and file paths may flow into
  GL-3 from FreeCAD; composite/geometric values (points, lines, curves,
  arrays) exist only inside the GL-3 world and leave it only through
  `GL3Export`.
- **Composite values crossing that boundary are serialized** (see
  `gerlib/serialize.py`) into a plain, JSON-safe "slot" format that
  explicitly carries a `defined`/`undefined` flag at every level — mirroring
  GL-3's own notion of definedness (`IFN`, `PRINT` vs `WRITE`). `GL3Export`
  never imports `gerlib` directly; it only reads this plain data.
- **Subroutine resolution:** a `GL3Program` may `CALL` other GL-3
  subroutines; these are resolved lazily by filename (`<NAME>.GL3`) via a
  `GL3Library` object holding a list of search directories, cached per
  recompute, re-read fresh on the next one (source editing today is via a
  plain external `.GL3` file + FreeCAD recompute; an in-app editor is a
  possible future addition).
- **Curve export** (Hermite spline output) is converted to a `Part.Wire`/
  single `Part.BSplineCurve` built from exact cubic Bezier segments, using
  the identity `B1 = P_i + T_i/3`, `B2 = P_{i+1} - T_{i+1}/3` — this
  reproduces the original Hermite spline exactly (verified numerically to
  ~1e-15), rather than relying on an approximate OCC interpolation.
- **Two curve-fitting opcodes, tracked via provenance flags:** `S03`
  (`dsn.py`) uses *uniform* parametrization (ignores actual distances
  between points); `S01` (`dspn.py`) uses *chord-length* parametrization
  (weights neighbor contributions by actual chord length — closer to what
  most CAD kernels, including OCC, do internally). Every `Spline` carries
  `opcode`/`parametrization` fields recording which method produced it —
  relevant not just for export, but for future rules about which curve
  types are valid input to surface generation. Because chord-length
  parametrization can give a *different* effective tangent magnitude on
  either side of the same node (each segment rescales by its own chord
  length), `Spline` also supports per-segment tangent pairs
  (`segment_tangents`) in addition to the simpler shared per-node
  `tangents` (which remains sufficient for `S03`).

## Installing as a FreeCAD workbench

Copy (or clone) this whole repository into your FreeCAD user `Mod`
directory, so that `InitGui.py` ends up directly at
`Mod/NEGWorkbench/InitGui.py`:

- Windows: `%APPDATA%\FreeCAD\Mod\NEGWorkbench`
- Linux: `~/.local/share/FreeCAD/Mod/NEGWorkbench`
- macOS: `~/Library/Preferences/FreeCAD/Mod/NEGWorkbench`

Restart FreeCAD; "NEG/GL3" should appear in the workbench selector.

Status: **three commands so far** — "Create GL3 Library" (creates a
`GL3Library` object), "Create GL3 Program" (creates a `GL3Program`
from a `.GL3` file, in/out properties auto-generated from its SUBRO
header), and "Create GL3 Export" (from a `GL3Program`'s selected
composite output, builds a `GL3Export` with a real `Part` shape).
More commands (editing a Library's search paths via a UI dialog, ...)
will be added incrementally as needed.

**Localization:** all user-facing strings are wrapped in
`QT_TRANSLATE_NOOP(context, text)` (source language: English) so that
translations can be added later as `.ts`/`.qm` files under
`translations/`, without touching the code — same mechanism FreeCAD's
own Arch/Draft workbenches use. No `.ts`/`.qm` files exist yet; this is
just future-proofing.

## Running the tests (no FreeCAD required)

```bash
cd gl3
python3 gl3_test.py                    # interpreter regression tests
python3 -m gerlib.test_serialize       # serialization round-trip
python3 -m gerlib.test_s01             # S01 (chordal) vs S03 (uniform) on real profile data
python3 test_dcoos3_tra23.py           # DCOOS3/TRA23 pure geometry (gerlib only)
python3 test_dcoos3_tra23_interpreter.py # DCOOS3/TRA23 on real GL3 source (parse_program + Interpreter.run())
python3 -m gl3fc.test_offline          # GL3Library/GL3Program, mocked FreeCAD
python3 -m gl3fc.test_props_offline    # add_property() Hidden/ReadOnly status wiring
python3 -m gl3fc.test_parse_ref_offline # parse_ref() incl. array-index '(N)' syntax
python3 -m gl3fc.test_export_offline   # GL3Export dispatch + Bezier math (build_shape only)
python3 -m gl3fc.test_gl3_export_offline    # GL3Export.execute() end-to-end ('Objekt.Vystup' reference + JSON parsing)
python3 -m gl3fc.test_claim_children_offline    # GL3Export shows as GL3Program's tree child, incl. document-restore ordering race
python3 -m gl3fc.test_composite_input_offline   # composite in: params (e.g. HLOCUT.gl3 'P') - reference + shadow Link
cd ..
python3 test_gl3_commands_offline.py   # workbench commands (Library/Program/Export creation), mocked FreeCAD/FreeCADGui
python3 test_init_no_file_offline.py    # Init.py registers gl3fc.* in sys.modules at startup, simulates real FreeCAD exec()
python3 test_initgui_no_file_offline.py # InitGui.py survives real FreeCAD exec() (separate globals/locals)
```

## Acknowledgments

- Original NEG/GL-3 language and methodology: LET Kunovice / Aircraft
  Industries a.s. (see "Historical context" above).
- Development assisted by Claude (Anthropic); see git commit trailers
  (`Co-authored-by: Claude <noreply@anthropic.com>`).

## License

MIT — see [LICENSE](LICENSE).
