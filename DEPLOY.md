# Publishing EduNexus for testers (GitHub + Streamlit Community Cloud)

GitHub stores the code; **Streamlit Community Cloud** runs it from your GitHub repository and
gives you a link such as `https://edunexus-demo.streamlit.app` (free).

## What is published — and what is not

| Published to GitHub | Stays on your PC only (blocked by `.gitignore`) |
|---|---|
| All app code, settings, tests | `data/TestStudents.xlsx` (original upload) |
| `data/EduNexus_public_demo.xlsx` — **made-up PIDM/ZID**, synthetic workload | `data/TestStudents_demo.xlsx` (original IDs) |
| `.streamlit/secrets.toml.example` (no real passwords) | `.streamlit/secrets.toml` (real passwords / API key) |

Testers sign in with a password. Viewers see all dashboards; only the admin password opens
**Administration**.

## Step 1 — Put the code on GitHub (GitHub Desktop, no commands)

1. Install **GitHub Desktop** (desktop.github.com) and sign in to your GitHub account.
2. *File → Add local repository…* → choose `E:\GEO-Programs\Claude\MyProject\EduNexus`.
   When asked, click **create a repository** here.
   - Name: `EduNexus` · leave *Git ignore* as **None** (the project already has `.gitignore`).
3. In the *Changes* list, confirm **no** `TestStudents.xlsx`, `TestStudents_demo.xlsx` or
   `secrets.toml` appear. Only `data/EduNexus_public_demo.xlsx` and `data/README.md` from `data/`.
4. Summary: `Initial EduNexus test release` → **Commit to main**.
5. **Publish repository** → tick **Keep this code private** (recommended) → Publish.

Command-line alternative:
```
cd /d E:\GEO-Programs\Claude\MyProject\EduNexus
git init -b main
git add .
git status            # check: no TestStudents*.xlsx, no secrets.toml
git commit -m "Initial EduNexus test release"
git remote add origin https://github.com/<your-user>/EduNexus.git
git push -u origin main
```

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to **share.streamlit.io** → *Continue with GitHub* → authorize Streamlit
   (for a private repo, also allow access to private repositories).
2. **Create app** → *Deploy a public app from GitHub* (it will inherit privacy from the repo).
   - Repository: `<your-user>/EduNexus` · Branch: `main` · Main file path: `app.py`
   - App URL: choose e.g. `edunexus-demo`
3. **Advanced settings**
   - Python version: **3.12**
   - Secrets: paste (choose your own passwords):
     ```toml
     [auth]
     viewer_password = "tester-password-here"
     admin_password  = "admin-password-here"
     # ANTHROPIC_API_KEY = "sk-ant-..."   # optional, enables the AI briefing
     ```
4. **Deploy**. First build takes a few minutes.

## Step 3 — Share with testers

- **Private repo → private app.** Community Cloud allows one private app per account.
  Invite testers by email: app **Settings → Sharing** → add their emails. They then also need the
  viewer password.
- **Public repo → public app.** Anyone with the link reaches the login page; the viewer password
  still protects the dashboards. Data in the repo is the made-up public demo only.

Send testers: the link, the viewer password, and what you want feedback on.

## Updating the test site

Change files on your PC → GitHub Desktop → **Commit** → **Push origin**. Community Cloud picks up
the change automatically within a minute or two.

## Notes

- Files uploaded on the hosted Administration page are temporary (lost when the app restarts).
  Real university data should not be uploaded to the public test site at all; it belongs on a
  university-hosted server or the future database connection.
- Regenerate the public demo after changing the generator:
  `python scripts/make_demo_data.py` then `python scripts/make_public_demo.py`.
- Change passwords any time in app **Settings → Secrets**; no redeploy needed.
