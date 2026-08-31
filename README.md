# Olist Delivery & Seller Performance Analytics

Module 2 group project. We use the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
to answer three connected business questions (see the assignment's business case doc):

1. How well are sellers fulfilling orders?
2. How well is the delivery network performing?
3. Does delivery performance relate to customer satisfaction (review score)?

## Tech stack

| Layer | Tool |
|---|---|
| Raw staging | MongoDB Atlas (Kaggle CSVs land here first, one collection per table) |
| Ingestion | [dlt](https://dlthub.com) (CSV → MongoDB, then MongoDB → BigQuery `raw` dataset) |
| Warehouse | BigQuery, star schema |
| Transformation | dbt (`raw` → `staging` → `marts`) |
| Data quality | dbt tests |
| Analysis | Python / pandas / SQLAlchemy, Jupyter |
| Reporting front-end | Streamlit, reading from a dedicated `reporting` datamart dataset |
| Orchestration | Dagster (asset graph across both dlt hops + dbt), scheduled via GitHub Actions |

See [docs/architecture/README.md](docs/architecture/README.md) for the full design.

## Repo layout

```
ingestion/          dlt pipelines: Kaggle CSV -> MongoDB olist_landing -> BigQuery olist_raw
warehouse/olist_dbt dbt project: raw -> staging -> marts (core + reporting datamart)
orchestration/      Dagster: wraps both dlt hops + dbt as one asset lineage graph
analysis/           Jupyter notebooks (deliverable)
dashboard/          Streamlit app reading the reporting datamart
docs/               architecture, GCP/MongoDB/dev setup
slides/             executive presentation deck
```

## Team roles

- **Ingestion / MongoDB + dlt (Vamsi):** `ingestion/` — owns both dlt hops (CSV → MongoDB); .
- **dbt / BigQuery transformation (Ian, Bang Lin, Shawn):** `warehouse/olist_dbt/` —  MongoDB → BigQuery, staging models, star schema
  (`marts/core`),creation of datamart (`marts/reporting`), dbt tests, overall `orchestration/`
- **Streamlit presentation (Priyanka):** `dashboard/` — reads only from the `reporting` datamart for cost saving/performance reason.


## Local dev setup

Every teammate develops against **their own personal GCP project** and **their own personal
MongoDB Atlas cluster** — never a shared one (GCP bills at the project level, and the Mongo
landing zone is just rebuilt from the same static CSVs every run, so there's nothing to keep
in sync between people's clusters). One project — the **submission project** — is the team's
actual deliverable, and only CI ever writes to it (see "Contributing" below).

**1. Create your own GCP project and MongoDB cluster** (one-time, per teammate)
   - GCP: [docs/gcp_setup.md](docs/gcp_setup.md) — new project, enable BigQuery API, `gcloud auth login`
   - MongoDB: [docs/mongodb_setup.md](docs/mongodb_setup.md) — new free Atlas cluster + database user
   - Kaggle: [kaggle.com/settings](https://www.kaggle.com/settings) → API → Create New Token (just need the username + key, no file download needed)

**2. Fill in your credentials — one file, one time**
   ```bash
   cp config/credentials.env.example config/credentials.env
   ```
   Edit `config/credentials.env` with your own `GOOGLE_CLOUD_PROJECT`, `KAGGLE_USERNAME`,
   `KAGGLE_KEY`, and `MONGODB_CONNECTION_URL` from step 1. This one file drives everything else
   — never edit the generated config files it feeds by hand.

**3. Run the setup script**
   ```bash
   bash scripts/setup_local_env.sh
   ```

   <details>
   <summary>What it does, step by step (9 steps, ~2-4 min — click to expand)</summary>

   1. Creates `config/credentials.env` from the template if it doesn't exist yet, and stops
      here on a first run so you can fill it in (see step 2 above).
   2. Creates `.venv` and installs every component's Python dependencies (auto-discovers every
      `requirements.txt` in the repo — orchestration/ is excluded, see its own README for why).
   3. Checks/prompts `gcloud auth login` and `gcloud auth application-default login`, then
      points `gcloud config` at your project.
   4. Generates `ingestion/.dlt/secrets.toml` (Mongo + BigQuery config for dlt) from
      `credentials.env`.
   5. Generates `~/.dbt/profiles.yml` — a personal `dbt_dev_<handle>` schema for `dev`, and
      `prod` pointing at `olist_raw`/`olist_warehouse`/`olist_reporting`, both within *your own*
      project.
   6. Confirms Kaggle auth is picked up from the environment (no `kaggle.json` needed).
   7. Downloads the Kaggle CSVs into `data/raw/`.
   8. Runs the ingestion pipeline: CSV → your MongoDB → your BigQuery `olist_raw`.
   9. Builds the warehouse: `dbt deps && dbt run && dbt test` (dev target, your own project).

   **Outcome:** by the end, your *own* GCP project and MongoDB cluster hold a fully populated,
   tested copy of the pipeline — `olist_raw`, `olist_warehouse` (star schema), and
   `olist_reporting` (datamart) all built from the same static Kaggle CSVs everyone else uses.
   Nothing here touches the team's shared submission project (see "Contributing" below) — this
   is your personal, disposable sandbox to develop and verify changes against.

   Safe to re-run any time `credentials.env` changes; it just redoes each step. Pass
   `--skip-pipeline` to only refresh config/dependencies (steps 1–6) without re-downloading or
   re-ingesting — useful once you've already got data loaded and just tweaked something like
   `DBT_DEV_HANDLE`.
   </details>

**4. Run the dashboard or notebooks**
   ```bash
   source .venv/bin/activate
   cd dashboard && streamlit run app.py
   ```
   For `analysis/*.ipynb` in VS Code, see
   [analysis/README.md](analysis/README.md#running-notebooks-in-vs-code-wsl) for picking the
   right kernel — there's a specific "requires ipykernel" failure mode documented there.

## Contributing: branch → commit → PR → merge

The repo lives at `ian-fl-liew/dsm2_ecommerce_delivery` on GitHub. `main` is protected (repo
owner: enable **Settings → Branches → require a pull request before merging**). All 5 of us are
added as **collaborators with Write access** (repo owner: Settings → Collaborators and teams →
Add people) — that changes the setup step below versus a typical open-source contribution flow.

**Setup (one-time per teammate):** since you have Write access, just clone the repo directly —
no fork needed:
```bash
git clone https://github.com/ian-fl-liew/dsm2_ecommerce_delivery.git
cd dsm2_ecommerce_delivery
```
(If you'd rather fork anyway — that still
works: fork on GitHub, clone your fork, `git remote add upstream
https://github.com/ian-fl-liew/dsm2_ecommerce_delivery.git`, and substitute `upstream` for
`origin` in the branch/push commands below. Only actually necessary for someone *without* Write
access.)

1. **Branch per task** off an up-to-date `main`:
   ```bash
   git checkout main && git pull
   git checkout -b feature/<short-description>   # e.g. feature/dim-seller
   ```
   Prefix by type: `feature/…`, `fix/…`, `docs/…`.
2. **Make your changes**, then commit in small, reviewable chunks with imperative-mood messages
   describing *why*, not just what (e.g. `Add dim_seller to unblock seller performance mart`,
   not `updates`).
3. **Push your branch** and open a **Pull Request** into `main`:
   ```bash
   git push -u origin feature/<short-description>
   ```
   Fill in what changed and why; link the relevant business question/model if applicable.
4. **Get at least one teammate's review/approval** before merging if you are changing a shared component — the reviewer should confirm
   `dbt build`/`dbt test` pass locally for dbt changes, and that nothing writes to the submission
   project directly (see `docs/gcp_setup.md`).
5. **Merge** (squash merge, to keep `main`'s history one commit per change) — this is what
   triggers `.github/workflows/ci.yml` to rebuild the submission project from source.
6. **Sync back up**: `git checkout main && git pull && git branch -d feature/<short-description>`.

**Nobody pushes straight to `main`** — even with Write access, branch protection blocks it;
every change goes through a PR + review, same as the fork-based flow would require.

## Team workflow & communication

- **Channel:** _(***Discord (DSAI Mod2 Project)*** for project details and coordination, ***Whatsapp*** group for prompting); GitHub PR comments for anything code-specific, so the discussion stays attached
  to the change.
- **Task tracking:** GitHub Issues — communicate via Discord group.
- **Cadence (2-week timeline):** a short sync every 2–3 days (what's done, what's blocked, what's
  next) plus one longer working session before the  presentation to rehearse and
  reconcile the dashboard/notebooks/slides against whatever landed in `main` last.
- **Unblocking:** if you're stuck for more than a day, say so in the channel rather than sitting
  on it.
- **Definition of done for a PR:** relevant `dbt test`/notebook sanity checks pass locally,
  docs updated if behavior/architecture changed, at least one approval or review, CI green after merge.
