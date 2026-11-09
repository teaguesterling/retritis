# Sphinx config for helpfledgling.ai, the public site of the retritis suite.
# Stack copied from judgementalmonad.com (Sphinx + Furo + MyST). Palette and
# type are Teague's "Deep Field" identity, mapped onto Furo's CSS variables.

project = "Retritis"
author = "Teague Sterling"
copyright = "2026, Teague Sterling"

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
]

myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
]
myst_heading_anchors = 3

source_suffix = {".md": "markdown"}

templates_path = ["_templates"]

# docs/ also holds internal working files. They must never get a public URL.
# scripts/check_site_leaks.py re-checks the BUILT output in CI, so a drift
# here fails the deploy instead of publishing.
exclude_patterns = [
    "_build",
    "briefs/**",
    "superpowers/**",
    "rfcs/**",
    "learn/**",
    "index.html",
    "book/README.md",  # rendered through book/index.md's include
]

html_theme = "furo"
html_title = "Retritis"
html_show_sourcelink = False
html_copy_source = False

# Deep Field: day = alpine haze, night = deep field. Gold is the one accent.
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#a56a12",        # stellar gold (ink)
        "color-brand-content": "#255b83",        # ocean (links)
        "color-background-primary": "#f6f9fb",
        "color-background-secondary": "#eaf0f3",
        "color-foreground-primary": "#12202f",
        "color-foreground-muted": "#425264",
        "color-background-border": "#cdd9e2",
        "color-admonition-background": "#eef3f7",
        "font-stack": '"IBM Plex Sans", system-ui, sans-serif',
        "font-stack--monospace": '"IBM Plex Mono", ui-monospace, monospace',
        "font-stack--headings": '"Spectral", Georgia, serif',
    },
    "dark_css_variables": {
        "color-brand-primary": "#e8a840",
        "color-brand-content": "#7cb8e2",
        "color-background-primary": "#0f1626",
        "color-background-secondary": "#080d17",
        "color-foreground-primary": "#e8eef4",
        "color-foreground-muted": "#9fb1c4",
        "color-background-border": "#1e2f47",
        "color-admonition-background": "#131f34",
    },
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}

html_static_path = ["_static"]
html_css_files = [
    "https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap",
    "custom.css",
]
