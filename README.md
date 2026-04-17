## Internal Proposal Generation Tool – V1

This is a Flask-based internal web application for composing and generating proposal documents, following the V1 blueprint (local auth, local storage, docxtpl-based Word export).

For a deeper architectural description, see `ARCHITECTURE.md`.

### Prerequisites

- Python 3.11+ (works on 3.14 with psycopg3)
- PostgreSQL instance you can connect to
- Windows PowerShell (commands below assume Windows paths)

### 1. Create virtual environment and install dependencies

From the project root (`c:\Shrilekha\ProposalGenerator`):

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure PostgreSQL and environment

- Create a database and user, for example:
  - Database: `proposal_db`
  - User: `proposal_user`
  - Password: `proposal_password`

You can either:

- Use the default URL in `config.py`:
  - `postgresql+psycopg://proposal_user:proposal_password@localhost/proposal_db`
- Or override via environment variable in PowerShell:

```bash
$env:DATABASE_URL = "postgresql+psycopg://proposal_user:proposal_password@localhost/proposal_db"
$env:SECRET_KEY = "some-long-random-secret"
```

### 3. Initialize the database schema

In the activated virtualenv and project root:

```bash
set FLASK_APP=run.py
flask db init     # only once, on a brand-new project
flask db migrate -m "Add engagement_type, ProposalVariable, ModuleSectionMap, version_description"
flask db upgrade
```

If you already have migrations, create a new migration for the refactor and run `flask db upgrade`. Then seed the module–section mapping:

```bash
flask seed-module-sections
```

### 4. Prepare the master Word template (layout only)

The Word generator uses `docxtpl` and expects a master template at:

- `templates/master_proposal_template.docx` (relative to the project root)

**Important:** The template must be **layout only**. All proposal body content comes from the database (sections, variables). Do not put static proposal text in the `.docx`.

Use **double-brace** docxtpl placeholders only (remove any single-brace placeholders like `{CustomerName}`):

- **Metadata:** `{{ proposal_title }}`, `{{ customer_name }}`, `{{ partner_name }}`, `{{ industry }}`, `{{ engagement_type }}`, `{{ proposal_to_line }}`, `{{ generated_date }}`, `{{ version_number }}`
- **Proposal variables (if set):** `{{ txn_volume }}`, `{{ commitment_tenure }}`, `{{ modules_in_scope }}`, `{{ commercials_validity_date }}`, etc.

**Body – sections (content from DB):**

```jinja
{% for section in sections %}
{{ section.title }}

{{ section.content }}

{% endfor %}
```

**Feature appendix:**

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

**Version timeline (Change Log):**

```jinja
{% for v in version_timeline %}
v{{ v.version_number }} – {{ v.generated_date }} – {{ v.description }}
{% endfor %}
```

### 5. Run the app

With the virtualenv active:

```bash
set FLASK_APP=run.py
flask run
```

The app will be available at `http://127.0.0.1:5000/`.

### 6. Create the first admin user

1. Open `http://127.0.0.1:5000/auth/init-admin` in your browser.
2. Fill in name, email, password.
3. Submit to create the first `admin`.

After this, log in via `/auth/login` using that account.

### 7. Configure section templates (admin-only)

To model your “master” proposal structure (e.g., the long document you pasted):

1. Log in as the `admin` user.
2. Click **Section Templates** in the top navigation bar.
3. For each main section you want:
   - Create or edit a template with:
     - **Section key** (e.g., `introduction`, `platform_overview`, `scope`, `solution_approach`, etc.).
     - **Title** (e.g., `Introduction`, `vuSmartMaps – Platform Overview`).
     - **Default content** – paste your long blurb (you can format it using the editor).
     - Leave “Enabled by default” checked if you want it in every new proposal.
4. Click **Save Templates**.

These templates are **global defaults** and are not changed when you edit a specific proposal.

### 8. Create and edit a proposal

1. Log in (as admin or a presales user).
2. Go to the **Proposals** dashboard.
3. Click **Create Proposal** and fill in:
   - Title, Customer name, Partner name (optional), Industry
   - **Engagement type:** Direct (VuNet to customer) or Partner-led (VuNet via partner).
   - **Modules in scope (optional):** Select one or more modules (e.g. vuInfra360, vuLogX). If selected, only sections mapped to those modules are enabled; otherwise template defaults apply.
4. Submit – the new proposal is created with sections copied from `SectionTemplate` (and optionally enabled by module mapping).
5. Click **Edit** on the proposal:
   - Set **Proposal variables** (e.g. txn_volume, commitment_tenure) for use in the Word template.
   - Reorder sections by drag-and-drop; enable/disable sections; edit section content in the rich text editor (Quill).
6. Save changes – edits are stored on that proposal only.

### 9. Generate a Word document and version timeline

1. From the proposal’s **View** page, optionally enter a **Version description** (e.g. “initial draft”, “updated scope”, “pricing revision”) for the Change Log.
2. Click **Generate Word**.
3. A new `GeneratedFile` record is created and the `.docx` is written under:
   - `generated_files/<year>/<CustomerName>_v<version>.docx`
4. The **Proposal version timeline** table shows all versions with description and download link. Use this for a consulting-style Change Log in the document (via the `version_timeline` placeholder in the template).

Each generation increments `version_number` for that proposal.

### 10. Health check endpoint (for cron)

- JSON summary at:
  - `/health/weekly-summary`
- Returns:
  - Disk usage for `generated_files/`
  - DB size in MB (if permissions allow)

You can call this via a weekly cron job and alert based on thresholds.

### Core features (V1, consulting-style refactor)

- Local email/password authentication (admin / presales roles)
- **Engagement type:** Direct vs Partner-led proposals (title line in document)
- **Module-driven sections:** Optional module selection at create time; sections auto-enabled via `ModuleSectionMap` (seed with `flask seed-module-sections`)
- Proposal dashboard with search and status filtering
- Proposal creation, editing, cloning, and locking
- **Proposal variables** (e.g. txn_volume, commitment_tenure) for template placeholders
- Section enable/disable, drag-and-drop reordering, and rich text editing (Quill)
- Admin-defined section templates; Word template is **layout only** (content from DB)
- Snapshot-based sections and features per proposal; **feature appendix** in Word
- **Version timeline** and optional version description per generation (Change Log)
- Word document generation via `docxtpl`; generated files under `generated_files/<year>/<CustomerName>_vX.docx`
- Basic weekly health JSON endpoint at `/health/weekly-summary`

