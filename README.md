## Internal Proposal Generation Tool – V1

This is a Flask-based internal web application for composing and generating proposal documents, following the V1 blueprint (local auth, local storage, docxtpl-based Word export).

### Quick start (development)

1. Create and activate a virtualenv, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate  # on Windows
pip install -r requirements.txt
```

2. Set up the database (PostgreSQL) and environment:

- Create a database (e.g. `proposal_db`) and a user with access.
- Optionally set `DATABASE_URL` and `SECRET_KEY` in your environment.

3. Initialize the database:

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

4. Run the app:

```bash
flask --app run.py run
```

5. Create the first admin user:

- Visit `/auth/init-admin` in your browser and submit the form.

### Core features (V1)

- Local email/password authentication (admin / presales roles)
- Proposal dashboard with search and status filtering
- Proposal creation, editing, cloning, and locking
- Section enable/disable, drag-and-drop reordering, and rich text editing (Quill)
- Snapshot-based features and sections per proposal
- Word document generation via `docxtpl` using a master template
- Local file storage under `generated_files/` with per-year folders
- Basic weekly health JSON endpoint at `/health/weekly-summary`

