"""
Standard section keys and module/section mapping for consulting-style proposals.
"""

# Standard section keys (structured naming for modular automation)
STANDARD_SECTION_KEYS = [
    "cover_page",
    "introduction",
    "platform_overview",
    "platform_differentiation",
    "scope_of_engagement",
    "inventory",
    "applications_in_scope",
    "functional_features",
    "solution_approach",
    "implementation_approach",
    "deliverables",
    "deployment_architecture",
    "hardware_requirements",
    "training",
    "post_implementation_support",
    "risk_management",
    "pricing",
    "terms_conditions",
    "appendix_features",
]

# Supported modules (for filtering features by module_tag)
SUPPORTED_MODULES = [
    "vuInfra360",
    "vuApp360",
    "vuTXN360",
    "vuLogX",
    "RUM",
    "SyntheticMonitoring",
]

# Default module -> section_key mapping (used to seed ModuleSectionMap)
DEFAULT_MODULE_SECTION_MAP = [
    ("vuInfra360", "infrastructure_observability"),
    ("vuApp360", "application_observability"),
    ("vuTXN360", "transaction_observability"),
    ("vuLogX", "log_analytics"),
    ("RUM", "rum_observability"),
    ("SyntheticMonitoring", "synthetic_monitoring"),
]

from typing import Final, List, Dict, Any


# Standard proposal variable keys (consulting-style)
STANDARD_PROPOSAL_VARIABLE_KEYS: Final[List[str]] = [
    "modules_in_scope",
    "components",
    "commercials_validity_date",
    "commitment_tenure",
    "implementation_cost",
    "txn_volume",
    "tps_peak",
    "infra_nodes",
    "log_volume",
]


# Default section templates used to auto-seed the SectionTemplate table
# on a fresh database. Content is intentionally high-level; you can
# further refine it via the admin UI without having to recreate rows
# or ordering every time you reset the DB.
DEFAULT_SECTION_TEMPLATES: Final[List[Dict[str, Any]]] = [
    {
        "section_key": "cover_page",
        "title": "Cover Page",
        "default_content": "",
    },
    {
        "section_key": "introduction",
        "title": "Introduction",
        "default_content": "",
    },
    {
        "section_key": "platform_overview",
        "title": "Platform Overview",
        "default_content": "",
    },
    {
        "section_key": "platform_differentiation",
        "title": "Platform Differentiation",
        "default_content": "",
    },
    {
        "section_key": "scope_of_engagement",
        "title": "Scope of Engagement",
        "default_content": "",
    },
    {
        "section_key": "inventory",
        "title": "Inventory",
        "default_content": "",
    },
    {
        "section_key": "applications_in_scope",
        "title": "Applications in Scope",
        "default_content": "",
    },
    {
        "section_key": "functional_features",
        "title": "Functional Features",
        "default_content": "",
    },
    {
        "section_key": "solution_approach",
        "title": "Solution Approach",
        "default_content": "",
    },
    {
        "section_key": "implementation_approach",
        "title": "Implementation Approach",
        "default_content": "",
    },
    {
        "section_key": "deliverables",
        "title": "Deliverables",
        "default_content": "",
    },
    {
        "section_key": "deployment_architecture",
        "title": "Deployment Architecture",
        "default_content": "",
    },
    {
        "section_key": "hardware_requirements",
        "title": "Hardware Requirements",
        "default_content": "",
    },
    {
        "section_key": "training",
        "title": "Training",
        "default_content": "",
    },
    {
        "section_key": "post_implementation_support",
        "title": "Post-implementation Support",
        "default_content": "",
    },
    {
        "section_key": "risk_management",
        "title": "Risk Management",
        "default_content": "",
    },
    {
        "section_key": "pricing",
        "title": "Pricing",
        "default_content": "",
    },
    {
        "section_key": "terms_conditions",
        "title": "Terms & Conditions",
        "default_content": "",
    },
    {
        "section_key": "appendix_features",
        "title": "Appendix – Feature Details",
        "default_content": "",
    },
]
