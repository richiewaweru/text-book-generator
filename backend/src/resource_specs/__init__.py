"""YAML-backed resource specification registry."""

from resource_specs.candidates import (
    PAGE_PSEUDO_COMPONENT_IDS,
    RoleCandidateSet,
    resolve_required_role_candidates,
    resolve_role_candidates,
    resolve_section_candidates,
)
from resource_specs.loader import (
    PRIMARY_RESOURCE_TYPE,
    get_primary_spec,
    get_spec,
    initialize_registry,
    list_spec_ids,
    load_all_specs,
)
from resource_specs.schema import ResourceSpec, SectionSpec

__all__ = [
    "PAGE_PSEUDO_COMPONENT_IDS",
    "PRIMARY_RESOURCE_TYPE",
    "ResourceSpec",
    "RoleCandidateSet",
    "SectionSpec",
    "get_primary_spec",
    "get_spec",
    "initialize_registry",
    "list_spec_ids",
    "load_all_specs",
    "resolve_required_role_candidates",
    "resolve_role_candidates",
    "resolve_section_candidates",
]
