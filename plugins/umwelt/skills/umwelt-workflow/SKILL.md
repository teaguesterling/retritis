---
name: umwelt-workflow
description: Define and compile agent permission policy with CSS-like .umw world files (what an agent may see/edit/call/trigger). Largely internal infrastructure — its compiled SQLite policy is consumed by kibitzer/lackpy/sandbox.
---
# umwelt — agent permission policy

CLI (no MCP server). Author `.umw` world files (CSS-like cascade) declaring read/edit paths,
callable tools, and resource limits; compile to the SQLite policy the other tools read.

- `umwelt parse <file>` — parse a .umw file to its AST
- `umwelt inspect <file>` — show the resolved policy properties
- `umwelt check <file>` — validate a world file
- compiled policy → `.kibitzer/policy.db`, consumed by kibitzer (enforcement), lackpy (program validation), and sandbox builders (nsjail/bwrap)
