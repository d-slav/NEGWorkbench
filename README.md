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

Status: **one command so far** — "Vytvořit GL3 Library" (creates a
`GL3Library` object). More commands (creating a `GL3Program` from a
`.GL3` file, creating a `GL3Export`, editing a Library's search paths)
will be added incrementally once this first one is confirmed solid.

## Running the tests (no FreeCAD required)

```bash
cd gl3
python3 gl3_test.py                 # interpreter regression tests
python3 -m gerlib.test_serialize    # serialization round-trip
python3 -m gerlib.test_s01          # S01 (chordal) vs S03 (uniform) on real profile data
python3 -m gl3fc.test_offline       # GL3Library/GL3Program, mocked FreeCAD
python3 -m gl3fc.test_export_offline # GL3Export dispatch + Bezier math
cd ..
python3 test_gl3_commands_offline.py # workbench command (GL3Library creation), mocked FreeCAD/FreeCADGui
```

## Acknowledgments

- Original NEG/GL-3 language and methodology: LET Kunovice / Aircraft
  Industries a.s. (see "Historical context" above).
- Development assisted by Claude (Anthropic); see git commit trailers
  (`Co-authored-by: Claude <noreply@anthropic.com>`).

## License

MIT — see [LICENSE](LICENSE).
