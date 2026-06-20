-- bypass.sql — "do retritis-tool sessions still reach for raw shell?" as SQL.
--
-- The substrate-native successor to bypass_probe.py: instead of hand-parsing
-- transcript JSONL in Python, it queries fledgling's conversation parser
-- (the duck-parser). This is Step 0 of the agent-riggs duck-parser plan
-- (see agent-riggs docs/superpowers/specs/2026-06-20-system4-synthesis.md);
-- Step 1 folds this into agent-riggs as a SQL view the ratchet consumes.
--
-- Requires fledgling's conversation macros (tool_calls / bash_commands /
-- sessions), which ship with fledgling-mcp as fledgling/sql/conversations.sql.
-- Run, e.g.:
--
--   CONV=$(python3 -c "import importlib.util as u, os; \
--     s=u.find_spec('fledgling'); \
--     print(os.path.join(os.path.dirname(s.origin),'sql','conversations.sql'))")
--   [ -f "$CONV" ] || CONV=~/Projects/fledgling/sql/conversations.sql   # editable layout
--   duckdb -c "SET VARIABLE conversations_root='$HOME/.claude/projects'; \
--              .read $CONV
--              .read scripts/bypass.sql"
--
-- NOTE: classification uses fledgling's bash *categories* (file_search /
-- build_tools / git_write), which are broader than bypass_probe.py's precise
-- recursive-grep patterns — so counts differ from the Python probe. Reconciling
-- the taxonomy (or adopting fledgling's as canonical) is a refinement.

WITH calls AS (SELECT * FROM tool_calls()),
plug AS (   -- per session: retritis-plugin call counts + which project
  SELECT session_id,
    any_value(regexp_extract(source_file, '.claude/projects/([^/]+)/', 1)) AS project_dir,
    count(*) FILTER (WHERE tool_name LIKE 'mcp__plugin_squackit%') AS squackit,
    count(*) FILTER (WHERE tool_name LIKE 'mcp__plugin_blq%')      AS blq,
    count(*) FILTER (WHERE tool_name LIKE 'mcp__plugin_jetsam%')   AS jetsam
  FROM calls GROUP BY session_id
),
qual AS (   -- availability proxy: >=1 retritis call; exclude maintenance sessions
  SELECT p.* FROM plug p JOIN sessions() s USING (session_id)
  WHERE (squackit + blq + jetsam) > 0
    AND p.project_dir NOT ILIKE '%retritis%'
    -- AND s.started_at >= now()::timestamp - INTERVAL 14 DAY   -- uncomment to window
),
byp AS (    -- raw-shell ops a structured tool covers, in qualifying sessions
  SELECT category, count(*) AS n
  FROM bash_commands() bc JOIN qual q USING (session_id)
  GROUP BY category
)
SELECT tool, retritis_calls, shell_bypasses,
       round(retritis_calls::DOUBLE
             / nullif(retritis_calls + shell_bypasses, 0), 2) AS preference
FROM (
  SELECT 'squackit' AS tool, (SELECT sum(squackit) FROM qual) AS retritis_calls,
         COALESCE((SELECT n FROM byp WHERE category = 'file_search'), 0) AS shell_bypasses
  UNION ALL
  SELECT 'blq', (SELECT sum(blq) FROM qual),
         COALESCE((SELECT n FROM byp WHERE category = 'build_tools'), 0)
  UNION ALL
  SELECT 'jetsam', (SELECT sum(jetsam) FROM qual),
         COALESCE((SELECT n FROM byp WHERE category = 'git_write'), 0)
) t
ORDER BY preference;
