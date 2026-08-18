# No `docs:` frontmatter here on purpose. Kit doc paths resolve as
# `workspace / <path>`, so a `docs/tools/*.md` reference is dead in every repo
# except lackpy's own source tree -- and it resolves to nothing silently.
# lackpy's default_tools.toml already attaches those docs per tool anyway.
# Apply a decided change and verify it.
# Measured: passes on every model tested, but ONLY when the intent also carries
# the procedure and the file's current text. See lackpy-delegation SKILL.md.
read_file
edit_file
run
