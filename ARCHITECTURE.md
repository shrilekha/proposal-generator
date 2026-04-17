# Architecture Overview

This document summarizes the internal architecture of the Proposal Generator V1 after the consulting-style refactor. The system remains **Flask + PostgreSQL + docxtpl**; the database stores all proposal content and the Word template controls layout only.

## Core design principle

- **Database stores all proposal content.** Section text, features, and variables live in `ProposalSection`, `ProposalFeature`, and `ProposalVariable`.
- **Word template is layout-only.** It must not contain static proposal body text. All body content comes from the DB via the docxtpl context.
- **Content flow:** Admin templates → `SectionTemplate` → Proposal creation → `ProposalSection` snapshot → Presales edits stored in `ProposalSection.content` → Word generation renders DB content.

## High-level design

- **Stack:** Flask (monolithic, Blueprints), PostgreSQL (SQLAlchemy), server-rendered HTML (Bootstrap 5, Quill, SortableJS), docxtpl, local file storage under `generated_files/`.
- **Engagement types:** Proposals can be **DIRECT** (VuNet to customer) or **PARTNER_LED** (VuNet via partner). Title line in the document reflects this.
- **Module-driven assembly:** `ModuleSectionMap` maps `module_tag` → `section_key`. When modules are selected at proposal creation, only matching sections are enabled.

## Folder structure

- `app/` – Flask package  
  - `models.py`, `constants.py` – data models and standard keys  
  - `auth/`, `proposals/`, `admin/`, `health/` – blueprints  
  - `services/word_generator.py`, `services/file_storage.py`  
  - `templates/` – Jinja2 HTML  
- `templates/` – project-level **Word** template: `master_proposal_template.docx`  
- `generated_files/<year>/` – generated `.docx` files  
- `config.py`, `run.py`, `requirements.txt`

## Data model

- **User** – `id`, `name`, `email`, `password_hash`, `role` (admin / presales), `created_at`, `is_active`.
- **Proposal** – `id`, `title`, `customer_name`, `partner_name`, `industry`, `status` (draft / locked), **`engagement_type`** (DIRECT | PARTNER_LED), `created_by`, `created_at`, `updated_at`. Relationships: `sections`, `features`, `generated_files`, **`variables`**.
- **ProposalSection** – `id`, `proposal_id`, `section_key`, `title`, `content` (HTML), `order_index`, `is_enabled`. Content comes from DB only.
- **ProposalFeature** – `id`, `proposal_id`, `module_tag`, `feature_name`, `description`, `order_index`. Used for module-driven appendices.
- **GeneratedFile** – `id`, `proposal_id`, `filename`, `file_path`, `generated_at`, `version_number`, **`version_description`** (optional, for Change Log).
- **ProposalVariable** – `id`, `proposal_id`, `variable_key`, `variable_value`. Consulting-style variables (e.g. `txn_volume`, `commitment_tenure`) exposed in docxtpl context.
- **SectionTemplate** – admin-defined default sections; copied into each new proposal.
- **ModuleSectionMap** – `id`, `module_tag`, `section_key`. Maps modules to section keys for auto-enabling sections when modules are selected.

## Word template (layout only)

The master `.docx` must **not** contain static proposal body text. Use only:

- **Placeholders (double braces):**  
  `{{ proposal_title }}`, `{{ customer_name }}`, `{{ partner_name }}`, `{{ industry }}`, `{{ engagement_type }}`, `{{ proposal_to_line }}`, `{{ generated_date }}`, `{{ version_number }}`.
- **Proposal variables (flattened into context):**  
  `{{ txn_volume }}`, `{{ commitment_tenure }}`, `{{ modules_in_scope }}`, etc., if set on the proposal.
- **Body – sections loop (content from DB):**

```jinja
{% for section in sections %}
{{ section.title }}

{{ section.content }}

{% endfor %}
```

- **Feature appendix:**

```jinja
{% if features %}
Appendix – Feature Details
{% for f in features %}
Module: {{ f.module_tag }}
Feature: {{ f.feature_name }}
Description:
{{ f.description }}
{% endfor %}
{% endif %}
```

- **Version timeline (Change Log):**

```jinja
{% for v in version_timeline %}
v{{ v.version_number }} – {{ v.generated_date }} – {{ v.description }}
{% endfor %}
```

Remove any old single-brace placeholders (e.g. `{CustomerName}`).

## docxtpl context (word_generator)

- **Proposal:** `proposal_title`, `customer_name`, `partner_name`, `industry`, `engagement_type`, `proposal_to_line` (“Proposal to X” or “Proposal to Partner for Customer”), `generated_date`, `version_number`.
- **Sections:** list of `{ title, content, section_key, order_index }` for rows with `is_enabled == True`, sorted by `order_index`.
- **Features:** list of `{ module_tag, feature_name, description, order_index }` sorted by `order_index`.
- **version_timeline:** list of `{ version_number, generated_date, description }` for all generated versions plus the current one.
- **Proposal variables:** flattened into context so `{{ txn_volume }}` etc. work.

## Standard section keys

Used for modular automation and consistency:

`cover_page`, `introduction`, `platform_overview`, `platform_differentiation`, `scope_of_engagement`, `inventory`, `applications_in_scope`, `functional_features`, `solution_approach`, `implementation_approach`, `deliverables`, `deployment_architecture`, `hardware_requirements`, `training`, `post_implementation_support`, `risk_management`, `pricing`, `terms_conditions`, `appendix_features`.

## Modules and ModuleSectionMap

Supported modules: `vuInfra360`, `vuApp360`, `vuTXN360`, `vuLogX`, `RUM`, `SyntheticMonitoring`. Default mapping (seed with `flask seed-module-sections`):

- vuInfra360 → infrastructure_observability  
- vuApp360 → application_observability  
- vuTXN360 → transaction_observability  
- vuLogX → log_analytics  
- RUM → rum_observability  
- SyntheticMonitoring → synthetic_monitoring  

When modules are selected at proposal creation, only sections whose `section_key` appears in the map for those modules are enabled; otherwise section default (from template) is used.

## File generation and backward compatibility

- Generated files: `generated_files/<year>/<CustomerName>_v<version>.docx`. `GeneratedFile` stores `filename`, `file_path`, `generated_at`, `version_number`, `version_description`.
- Existing proposals without `engagement_type` or variables still generate: defaults (e.g. DIRECT, empty variables) are applied so generation does not break.

## Key modules (summary)

- **app/proposals/routes.py** – Create (engagement_type, optional module_tags → section enablement), edit (engagement_type, proposal variables), clone (copies engagement_type and variables), generate (version_description).
- **app/services/word_generator.py** – Loads sections/features/variables/version_timeline from DB, builds full context, renders layout-only template.
- **app/constants.py** – `STANDARD_SECTION_KEYS`, `SUPPORTED_MODULES`, `DEFAULT_MODULE_SECTION_MAP`, `STANDARD_PROPOSAL_VARIABLE_KEYS`.
