# No `docs:` frontmatter here on purpose. Kit doc paths resolve as
# `workspace / <path>`, so a `docs/tools/*.md` reference is dead in every repo
# except lackpy's own source tree -- and it resolves to nothing silently.
# lackpy's default_tools.toml already attaches those docs per tool anyway.
# Read a captured failure and locate the code it implicates.
# Do not assume blq's ref_file carries the source at fault. On a single-frame
# assertion failure -- the common case -- it is the TEST file, because the
# traceback names nothing else, and a delegation that stops there will invent a
# source path. Resolve the implementation yourself and carry it.
events
status
find_names
read_file
