"""Add cwd parameter to jetsam workflow verbs and thread it through build_state/run_git_sync.

For each `@mcp.tool()` def in mcp/tools.py:
  - Add `cwd: str | None = None,` to the signature (last positional kwarg).
  - Replace `build_state()` calls inside the function with `build_state(cwd=cwd)`.
  - Replace `run_git_sync(args)` calls inside the function with `run_git_sync(args, cwd=cwd)`.

Plan-based verbs (show_plan, modify_plan, confirm, cancel) and the `git` passthrough
are skipped — they operate on plan IDs or already accept -C in their args.
"""

import re
import sys
from pathlib import Path

PATH = Path("/home/teague/Projects/jetsam/src/jetsam/mcp/tools.py")
text = PATH.read_text()

# Verbs to skip — these don't need cwd.
SKIP = {"show_plan", "modify_plan", "confirm", "cancel", "git"}

# Split file into [@mcp.tool() ... ] blocks.
# Find each `@mcp.tool()` followed by a def. Use a regex that captures
# the whole function body (until the next `@mcp.tool()` or end-of-file).

# We'll iterate by finding `@mcp.tool()` positions and processing each
# function block individually.
pat = re.compile(r"(@mcp\.tool\(\)\n\s+def )(\w+)(\()", re.MULTILINE)

new_chunks = []
last_end = 0
matches = list(pat.finditer(text))

for i, m in enumerate(matches):
    new_chunks.append(text[last_end:m.start()])
    verb = m.group(2)
    # Find the end of this function: the next @mcp.tool() or end-of-file.
    block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    block = text[m.start():block_end]

    if verb in SKIP:
        new_chunks.append(block)
        last_end = block_end
        continue

    # Step 1: Add cwd to the signature. Find the def line and the closing
    # `)` of its parameter list.
    # Pattern: `def NAME(...)` with multi-line params. Use balanced-paren
    # walk from the first `(` after the def.
    def_idx = block.index(f"def {verb}(")
    open_idx = def_idx + len(f"def {verb}")
    depth = 0
    close_idx = None
    for j in range(open_idx, len(block)):
        c = block[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                close_idx = j
                break
    assert close_idx is not None, f"unbalanced parens in {verb}"

    # Insert cwd param before the closing `)`. We need indentation matching.
    # Check if the function has any params already.
    params_text = block[open_idx + 1:close_idx]
    has_params = params_text.strip() != ""
    has_cwd = "cwd:" in params_text

    if not has_cwd:
        if has_params:
            # Multi-line case: params separated by newlines + indentation.
            # Find the indent of an actual param line (matches whitespace +
            # non-whitespace identifier-start) — NOT the closing `)` line.
            if "\n" in params_text:
                param_indent_match = re.search(r"\n([ \t]+)\w", params_text)
                indent = param_indent_match.group(1) if param_indent_match else "        "
                # The `)` is preceded by an indent (one level shallower than
                # the params). Find that too so we keep it.
                close_indent_match = re.search(r"\n([ \t]*)\)$", block[:close_idx + 1])
                close_indent = close_indent_match.group(1) if close_indent_match else ""
                # Ensure trailing comma on existing last param.
                before_close = block[:close_idx].rstrip()
                trailing_comma = "" if before_close.endswith(",") else ","
                insertion = (
                    trailing_comma + "\n" + indent + "cwd: str | None = None,\n" + close_indent
                )
                block = before_close + insertion + ")" + block[close_idx + 1:]
            else:
                # Single-line params: just append `, cwd=None`.
                block = block[:close_idx] + ", cwd: str | None = None" + block[close_idx:]
        else:
            # No existing params (e.g. status, tidy).
            block = block[:close_idx] + "cwd: str | None = None" + block[close_idx:]

    # Step 2: build_state() → build_state(cwd=cwd) inside this function.
    block = re.sub(r"\bbuild_state\(\)", "build_state(cwd=cwd)", block)

    # Step 3: run_git_sync(args) → run_git_sync(args, cwd=cwd) — only when
    # the call has exactly the `args` positional, not when cwd is already
    # present.
    block = re.sub(
        r"run_git_sync\(args\)",
        "run_git_sync(args, cwd=cwd)",
        block,
    )

    # Step 4: ALSO append a "cwd" doc line in the Args block when present.
    # Find the docstring's Args: section and inject "cwd: ..." before the
    # closing triple-quote of the docstring.
    docstring_pat = re.compile(r'("""[^"]*?Args:\n)(.*?)(\n\s+""")', re.DOTALL)
    def add_cwd_doc(dm):
        head, body, tail = dm.group(1), dm.group(2), dm.group(3)
        if "cwd:" in body:
            return dm.group(0)
        # Match the indent of an existing arg line.
        lines = body.splitlines()
        indent = ""
        for ln in lines:
            m2 = re.match(r"^(\s+)\w", ln)
            if m2:
                indent = m2.group(1)
                break
        if not indent:
            indent = "            "
        cwd_doc = f"{indent}cwd: Working-directory override for this call. Defaults to\n{indent}    the MCP server's cwd. Use to operate on a non-cwd repo without\n{indent}    falling back to the `git` passthrough."
        return head + body + "\n" + cwd_doc + tail
    block = docstring_pat.sub(add_cwd_doc, block, count=1)

    new_chunks.append(block)
    last_end = block_end

new_chunks.append(text[last_end:])
new_text = "".join(new_chunks)

if new_text == text:
    print("No changes")
    sys.exit(0)

PATH.write_text(new_text)
print(f"Patched {PATH}")
print(f"  +{new_text.count(chr(10)) - text.count(chr(10))} lines")
