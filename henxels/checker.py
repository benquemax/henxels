"""Run the henxels over a set of paths and collect findings.

This is the structure-and-placement core. Guards, digest and similarity layer on
top of this in their own modules.
"""

from __future__ import annotations

from pathlib import Path

from henxels.config.load import Config
from henxels.config.tree import resolve
from henxels.findings import Finding
from henxels.plugins import run_plugins
from henxels.rules.duplication import check_canonical
from henxels.rules.existence import check_required, check_root_required
from henxels.rules.naming import check_naming
from henxels.rules.placement import check_placement
from henxels.similarity import similarity_findings


def check_paths(
    config: Config,
    root: Path | str,
    rel_paths: list[str],
    check_existence: bool = True,
    check_duplication: bool = True,
) -> list[Finding]:
    """Validate ``rel_paths`` against the contract.

    ``check_existence`` runs the (folder-level) ``require`` henxels; it's on for a
    full scan and off for staged/partial checks to avoid flagging unrelated folders.
    ``check_duplication`` runs the canonical (block) and similarity (warn) henxels.
    """
    findings: list[Finding] = []

    for rel in rel_paths:
        resolved = resolve(config.tree, rel)
        findings.extend(check_placement(resolved))
        findings.extend(check_naming(resolved))

    if check_existence:
        findings.extend(check_required(config.tree, root))
        findings.extend(check_root_required(config.require, root))

    if check_duplication:
        findings.extend(check_canonical(config, rel_paths))
        findings.extend(similarity_findings(config, root, rel_paths))

    findings.extend(run_plugins(config, root, rel_paths))

    return findings
