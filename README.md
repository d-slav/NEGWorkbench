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
gl3data/                   - data files used by example/system programs
                           (airfoil coordinate files etc., e.g. E374.TXT)
gl3examples/               - sample .GL3 programs demonstrating usage
                           (TEHLO, E374 - call into gl3sys/ subroutines)
gl3sys/                    - "system" .GL3 subroutines (HLO, SCARA,
                           HLOCUT) - the reusable library routines,
                           as opposed to demo programs
gl3test/                   - internal .GL3 test programs for the Python
                           regression suite (TEST1, XPROC, IOTEST) -
                           not meant for everyday FreeCAD use
gl3/
    gl3_lang.py         - lexer, parser, AST for GL-3
    gl3_interpreter.py  - interpreter (Environment, CALL, I/O channels, ...)
    gl3_ops.py          - operation/command registry, type table
    gl3_analysis.py      - in:/out: parameter direction analysis
    gerlib/             - standalone 2D/3D geometry library (no GL-3/FreeCAD
                          dependency), one file per operation, named after
                          the original GL-3 opcode (ported from Fortran
                          where source is available)
    geplib/             - spatial (3D) GL-3 commands with no original
                          Fortran source available (DCOOS3, TRA23, Q00,
                          U00, ...), implemented directly from the
                          language specification; uses gerlib.types
                          (Point/Vector/...) for the underlying geometry
    gl3fc/               - FreeCAD integration layer:
        gl3_library.py   - GL3Library: search paths for called subroutines
        gl3_program.py   - GL3Program: FeaturePython object running one
                          top-level GL-3 subroutine, auto-generated in:/out:
                          properties
        gl3_export.py    - GL3Export: converts a GL3Program's composite
                          output into native FreeCAD geometry (Part::Shape)
                          with a real Placement
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
- **Path placeholders** (`gl3_placeholders.py`): any string used as a
  file/directory path — `GL3Program.SourceFile`, `GL3Library.SearchPaths`
  entries, and the filename argument of `IDEV` inside a `.GL3` program's
  own source — may contain `${workbench_path}` (this addon's install
  directory), `${fc_file_path}` (directory of the currently open FreeCAD
  document; error if the document was never saved), and, inside `IDEV`
  only, `${gl3_file_path}` (directory of the `.GL3` file *currently
  executing* — resolves per `CALL`, so a called subroutine's own `IDEV`
  sees its own directory, not the top-level program's). An unrecognized
  `${...}` name, or a recognized one that makes no sense in that context
  (e.g. `${gl3_file_path}` in `SearchPaths`), raises a clear error rather
  than silently doing the wrong thing. A freshly created `GL3Library`
  defaults `SearchPaths` to `["${workbench_path}/gl3sys"]` (kept as the
  placeholder itself, not pre-resolved, so it still works after the addon
  is moved/reinstalled elsewhere). `GL3Library.build_registry()` also
  always searches `${fc_file_path}` *first*, ahead of every directory
  listed in `SearchPaths` — so a `.GL3` file sitting next to the current
  FreeCAD document shadows a same-named one in the library search paths.
  If the document isn't saved yet, that step is silently skipped (no
  error) and only `SearchPaths` is searched.
- **`RecomputeOnOpenDoc`** (`GL3Program`, default `True`): `execute()`'s
  short-circuit cache (`self._exec_cache` — skip re-running the interpreter
  if `SourceFile`'s mtime, `Library`, and every `in:` value are unchanged
  since the last successful run) lives only on the Python `Proxy` instance
  — `__getstate__`/`__setstate__` intentionally return `None`, so nothing
  about it survives a save. Practically this means the *first* `execute()`
  after opening any document with a `GL3Program` always does a full
  re-run, even if literally nothing changed since it was last saved —
  which matters for programs with a multi-minute recompute time. This is
  the deliberate, safe default: since `SourceFile` is only ever read fresh
  from disk (never embedded in the `.FCStd`), it also catches edits made
  externally to the `.GL3` file, to a `CALL`-dependency file, or to the
  interpreter/addon code itself — none of which the cache signature
  tracks. Setting `RecomputeOnOpenDoc = False` opts out on the user's own
  judgment: the same signature is *also* persisted as a real (hidden)
  `_ExecCache` string property, which — unlike `self._exec_cache` — does
  survive save/reload, so the recompute-on-open is skipped if it still
  matches. Any actual input change (including editing `SourceFile` itself,
  or its mtime changing) still forces a real run regardless of this flag.
- **`EditCommand`** (`GL3Program`, default `'edit ${gl3_file_path}/${gl3_file_name}'`):
  a shell command line run by the "Edit GL3 Program" toolbar button
  (`NEG_EditProgram`, `gl3fc.gl3_program.resolve_edit_command`) —
  typically used to open `SourceFile` in an external editor. All four
  placeholders are available here: `${workbench_path}`/`${fc_file_path}`
  as usual, plus `${gl3_file_path}`/`${gl3_file_name}` (new — directory
  and filename-with-extension) resolved from this `GL3Program`'s own,
  already-resolved `SourceFile` — a separate, simpler resolution than the
  interpreter's per-`CALL`-frame one used inside `IDEV`, since no
  interpreter is running when this button is pressed. Runs non-blocking
  (`subprocess.Popen(..., shell=True)`) so FreeCAD doesn't wait for the
  editor to close.
- **`gl3_keywords.json`** (`gl3/`, FreeCAD-independent — sits next to
  `gl3_lang.py`/`gl3_ops.py`): per-keyword/opcode hover documentation
  (`type`, `syntax`, `comment`, `menu`, `html_help_file`), converted from
  a historical C++/MFC editor's own tooltip data (`Gl3_Keywords.h`/`.cpp`
  + `Gl3Key.dat`, see `gl3/tools/gl3key_import/README.md` for the binary
  format, provenance, and how to re-run the one-off conversion). Kept
  deliberately separate from the `_op_*` docstrings in `gerlib`/`geplib`,
  which document implementation details (original Fortran line numbers,
  internal variable names) for maintainers, not end-user syntax help —
  two different audiences, two different texts. Intended primarily for a
  future editor/language-server integration (hover, autocomplete), not
  currently read by the addon or interpreter at runtime.
- **`in-f:`/`out-f:` SUBRO header hint** (`gl3_lang.parse_subro_header`):
  a `B`-type (text) parameter's FC property is `App::PropertyString` by
  default (plain text — GL3's own type system doesn't distinguish "a
  filename" from "arbitrary text", they're the same `B` type), but the
  `-f` hint (`in-f:BJM`) says "this particular text is a filename",
  switching that one parameter's generated property to
  `App::PropertyFile` (a file-browse button) — but only for `in:`;
  `out-f:` is accepted (parses fine, useful as self-documentation for a
  nested `CALL` returning a computed filename) but never affects the FC
  property, since an *output* property being a file path makes no sense
  in FreeCAD. Deliberately implemented as a 4th, independent tuple
  element (`(name, size, direction, hint)`) rather than a third
  `direction` value (`"in-f"`) — `direction` itself stays strictly
  `"in"`/`"out"` everywhere, so none of the >10 places across the
  codebase that compare `direction == "in"`/`"out"` needed touching; only
  the one spot that picks the FC property type reads the hint at all.
- **`TYPE`/`TYPE1`/`TYPE2`/`TYPET`** (G13.md): unlike `PRINT`/`WRITE`
  (one output record *per object*), `TYPE` concatenates its *entire*
  parameter list — variables, expressions, **and literal string
  constants** — into a single unlabeled record (e.g. `TYPE,BO,QA,'
  LEZI NA KRIVCE T'` with `BO='BOD Q'` and `QA` a 3D point prints exactly
  `BOD Q 50.000 23.500 0.000   LEZI NA KRIVCE T`, matching the doc's own
  worked example verbatim). Implementing this surfaced a real, unrelated
  pre-existing gap: `PRINT`/`WRITE`'s own formatter (`_print_one`)
  handled only `Point` and plain scalars, silently unable to print a
  `Circle`, `Line`, `Vector`, any 3D composite type, or even a `B`
  (string) value (would crash on `float(value)`) — despite the spec
  itself showing worked examples for exactly those. Fixed with a shared
  `gl3_ops.format_components(prefix, value)`: the *number and meaning* of
  a value's printed components is driven by the variable's type letter
  (`P`/`V`→2 numbers, `C`→3, `L`→4, `Q`/`U`→3, `R`/`M`→6, `G`→7, `B`→the
  string itself), not the runtime type of the Python object, since e.g. a
  bare `gerlib.types.Point` doesn't know on its own whether it's "2D" or
  "3D". Chains/curves (`S`/`E`/`T`/`H`, variable node count) and surfaces
  (`F`, no implementation exists yet) raise a clear `NotYetImplemented`
  rather than guessing at a format — both `PRINT`/`WRITE` and `TYPE` now
  share this formatter, so the fix benefits both.
- **`out:K`/`out:I`/`out:J` (integer output) storage**: the interpreter
  always computes with plain Python `float` (even for `I`/`J`/`K`
  variables), and `_store_outputs()` used to `setattr()` that float
  straight onto the generated `App::PropertyInteger` — which at least
  some FreeCAD versions reject outright (`TypeError: type must be int,
  not float`) rather than silently truncating. Fixed by coercing with
  `int(round(value))` specifically when the property's native type is
  `App::PropertyInteger`. The offline test harnesses used elsewhere in
  this repo are more lenient than real FreeCAD here (they accept a float
  on any property type without complaint), which is exactly why this
  slipped through — `gl3fc.test_integer_output_offline` uses a
  purpose-built strict fake object that actually replicates the rejection
  to catch it.
- **Bare `IF`** (definedness test): `gl3_keywords.json` (the historical
  editor's own tooltip data) confirms `IF` and `IFN` were always two
  distinct, original keywords — `IF/p/akce` = "action conditioned on the
  object being *defined*", `IFN/p/akce` = "...being *undefined*" — but
  only `IFN` had ever been ported; `IF/p/...` simply failed to parse
  (the `IFx` regexes required exactly one letter after `IF`, no letter
  at all wasn't accepted). Fixed by making that letter optional in all
  three places it's matched (`IfBlock`/`THEN`, `IfShort` one-line form,
  and the backward-`GOTO` "repeat while" idiom), and giving
  `parse_condition()` the matched letter so it can tell bare `IF` apart
  from `IFN` (and every other `IFx`, whose fallback-to-undefined-test
  behavior when no relational operator is found is left exactly as it
  was, to avoid changing behavior for existing sources) — new `IsDefined`
  AST node mirrors the existing `IsUndefined` one, negated.

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
python3 test_dcoos3_tra23.py           # DCOOS3/TRA23/Q00/U00 pure geometry (geplib)
python3 test_dcoos3_tra23_interpreter.py # DCOOS3/TRA23 on real GL3 source (parse_program + Interpreter.run())
python3 test_then_else_endif.py        # G12.md IFxx/.../THEN...ELSE...ENDIF (incl. nesting, backward-compat THEN-only)
python3 -m gl3fc.test_offline          # GL3Library/GL3Program, mocked FreeCAD
python3 -m gl3fc.test_props_offline    # add_property() Hidden/ReadOnly status wiring
python3 -m gl3fc.test_parse_ref_offline # parse_ref() incl. array-index '(N)' syntax
python3 -m gl3fc.test_export_offline   # GL3Export dispatch + Bezier math (build_shape only)
python3 -m gl3fc.test_gl3_export_offline    # GL3Export.execute() end-to-end ('Objekt.Vystup' reference + JSON parsing)
python3 -m gl3fc.test_claim_children_offline    # GL3Export shows as GL3Program's tree child, incl. document-restore ordering race
python3 -m gl3fc.test_composite_input_offline   # composite in: params (e.g. HLOCUT.gl3 'P') - reference + shadow Link
python3 -m gl3fc.test_hidden_chain_drawing_offline  # INI...CLOSE hidden chain drawn directly onto GL3Program.Shape, incl. CALL joins/gaps
python3 -m gl3fc.test_path_placeholders_offline     # ${workbench_path}/${fc_file_path}/${gl3_file_path} in SourceFile/SearchPaths/IDEV
python3 -m gl3fc.test_recompute_on_open_offline     # RecomputeOnOpenDoc - skip recompute-on-open when signature unchanged, via persisted _ExecCache
python3 test_gl3_keywords_data.py       # gl3_keywords.json structure + consistency with gl3_ops.OPERATIONS/COMMANDS
python3 test_infile_hint.py             # in-f:/out-f: SUBRO header hint parsing (B-type filename disambiguation)
python3 -m gl3fc.test_infile_hint_offline  # in-f:/out-f: -> GL3Program FC property type (App::PropertyFile vs String)
python3 test_type_command.py            # TYPE/TYPE1/TYPE2/TYPET (G13.md) + fixed PRINT/WRITE object formatting
python3 -m gl3fc.test_integer_output_offline  # out:K (I/J/K) stores a real int, not float ("type must be int, not float")
python3 test_if_defined.py              # bare IF (definedness test, negation of IFN) - both original keywords, only IFN was ported before
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
