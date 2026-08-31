# No `docs:` frontmatter here on purpose. Kit doc paths resolve as
# `workspace / <path>`, so a `docs/tools/*.md` reference is dead in every repo
# except lackpy's own source tree -- and it resolves to nothing silently.
#
# default_tools.toml declares the same relative paths per tool, through the same
# dead join, so those are no better OUTSIDE the lackpy tree. The reason removing
# the frontmatter loses nothing is different and worth stating: registry.py does
# `resolved.docs = meta.docs`, OVERWRITING the per-tool docs list. Kit-level
# `docs:` was discarding the per-tool docs; dropping it restores them.
# Apply a decided change and verify it.
# Measured: passes on every model tested, but ONLY when the intent also carries
# the procedure and the file's current text. See lackpy-delegation SKILL.md.
read_file
edit_file
run
