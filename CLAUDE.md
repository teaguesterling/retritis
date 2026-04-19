## Retritis — Claude Code Plugin Marketplace

The retritis suite: palliative treatments for agent-assisted development.

### Structure

```
.claude-plugin/marketplace.json   — plugin catalog
plugins/
  blq/                            — build log query
  jetsam/                         — git workflow accelerator
  fledgling/                      — DuckDB code analysis
  squackit/                       — code intelligence MCP server
  kibitzer/                       — tool call observer
```

### Plugin anatomy

Each plugin follows the same pattern:

```
plugins/<name>/
  .claude-plugin/plugin.json      — manifest (name, description, version)
  .mcp.json                       — MCP server config
  skills/<name>-workflow/SKILL.md  — routing table + tool reference
  hooks/                          — optional PreToolUse warning hooks
    hooks.json                    — hook registration
    <name>-warn.sh                — hook script
```

### Adding a new plugin

1. Create `plugins/<name>/` with the structure above
2. The `.mcp.json` should use the tool's standard serve command
3. The skill should have a routing table: "instead of X, use Y"
4. Hooks are optional — add when the plugin's tools overlap with common Bash patterns
5. Add the plugin entry to `.claude-plugin/marketplace.json`
6. Update `README.md`

### Existing tools and their repos

| Plugin | Package | Repo | MCP command |
|--------|---------|------|-------------|
| blq | `pip install blq-cli` | teague/lq | `blq mcp serve` |
| jetsam | `pip install jetsam-mcp` | teague/jetsam | `jetsam serve` |
| fledgling | `pip install fledgling` | teague/source-sextant | `fledgling mcp serve` |
| squackit | `pip install squackit` | teague/squackit | `squackit mcp serve` |
| kibitzer | `pip install kibitzer` | teague/kibitzer | `kibitzer mcp serve` |

### Testing plugins

```bash
# Load a plugin locally for testing
claude --plugin-dir ./plugins/blq

# Or add the marketplace and install
/plugin marketplace add teaguesterling/retritis
/plugin install blq@retritis
```

### Conventions

- Plugin names match the tool name (lowercase)
- Skill names use `<tool>-workflow` pattern
- Hook scripts use `<tool>-warn.sh` pattern
- MCP server names match existing conventions
- Version in plugin.json tracks the plugin config version, not the tool version
