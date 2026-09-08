## Handoff summary

**Confirmed safely delivered** (last bundle merged, HEAD e78a44d): everything through the PRINT/WRITE error-format fix ([Error] program/line/operation: text).

**Lost in this session's container reset — needs to be redone from scratch:**

### 1. Small change (quick)

GL3Program.EditCommand default value: change from 'edit ${gl3_file_path}/${gl3_file_name}' to 'Notepad ${gl3_file_path}/${gl3_file_name}'. Touches: gl3/gl3fc/gl3_program.py, gl3_commands.py (docstring), test_gl3_commands_offline.py (assertions), README.md.

### 2. The big one: broad error-message sweep across gl3_interpreter.py

Goal: every GL3-program-level runtime mistake should surface as GL3RuntimeError with the standard [Error] program/line/operation: text format (via self._raise_gl3_error(operation, message)), not a bare NameError/ValueError/TypeError/KeyError/SyntaxError/OSError.

**Design rules established (important — apply these, don't re-derive):**

- Convert (GL3-program mistake → _raise_gl3_error): undefined variable/array element, wrong arg count, wrong type used, unregistered CALL target, IDEV file/channel problems, GET/READ record-too-short, SCALE/TRA23/DCOOS3 validation.
- Keep as NotYetImplemented but wrap message with self._format_report("Error", operation, message) for context (not _raise_gl3_error, since that always raises GL3RuntimeError): DATA on unsupported type (S/E/T/H/F), GET/READ on unsupported types, terminal read.
- Leave untouched (genuine internal bugs, not GL3-program mistakes — distinct exception type is a useful signal): unrecognized AST node type, unrecognized operator/relation string, COMMANDS/OPERATIONS registry lookup failures for a name that dispatch already matched.
- Threaded an operation parameter through shared helpers (_eval_array_ref, _set_indexed, _next_raw_line, _next_record, _component_count, _make_value, _assign_target) so nested calls can still report the right command name. Defaults to None → renders as - in the format, never crashes.
- For DATA specifically: use the literal command name "DATA" as operation (not the target variable name) — for consistency with how PRINT/SCALE/TRA23/DCOOS3/CALL/IDEV all use their own command keyword as operation, not an incidental variable name. (I made this mistake once mid-session — used the target variable name first, caught it via a test assertion mismatch, corrected it. Worth getting right the first time in the new thread.)

**All of this was implemented and fully passing** (23 pytest + full manual sweep, only the same ~11 pre-existing unrelated gerlib test failures) at the point of the reset — I have the design memorized (above) but the actual diff is gone and needs to be re-typed.

**Test files that needed updating** because they asserted the old bare exception types (this list is also worth having upfront to avoid re-discovering each one via trial and error): test_dcoos3_tra23_interpreter.py, test_dimen_input_guard.py, test_data_command.py, test_gl3_commands_offline.py (line ~294, except OSError → except Exception), gl3/gl3fc/test_offline.py (similar), gl3/gl3fc/test_short_traceback_offline.py (message content assertion). I'd also added a good chunk of new dedicated test coverage in test_error_categories.py for SCALE/TRA23/DCOOS3/CALL/IDEV/GET error formats — also gone, worth redoing.