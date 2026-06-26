"""Opt-in plugins — demoted optionals, off unless enabled in `plugins:`.

henxels' core is structure and placement. Markdown linting and frontmatter checks are
useful but secondary, so they live here and only run when the contract asks for them.
"""

from henxels.plugins.frontmatter import check_frontmatter
from henxels.plugins.markdown import check_markdown


def run_plugins(config, root, rel_paths):
    """Run whichever plugins the contract enables. Returns findings."""
    if not config.plugins:
        return []
    findings = []
    findings.extend(check_frontmatter(config, root, rel_paths))
    findings.extend(check_markdown(config, root, rel_paths))
    return findings


__all__ = ["run_plugins", "check_frontmatter", "check_markdown"]
