# Deployment Guide (No Coding Required)

Follow these steps in order. Total time: ~20-30 minutes.

## Step 1 — Get a Claude API key

1. Go to https://console.anthropic.com and sign up / log in.
2. Go to **Settings → API Keys → Create Key**.
3. Copy the key (starts with `sk-ant-...`). Save it somewhere safe — you'll paste it
   into Render in Step 4. You will not be able to see it again after leaving the page.
4. Note: this requires adding a small amount of billing credit to your Anthropic
   account (a few dollars is enough for this assignment).

## Step 2 — Create a GitHub account (if you don't have one)

1. Go to https://github.com and sign up (free).

## Step 3 — Upload this project to GitHub

**Easiest way (no command line):**

1. On github.com, click the **+** icon (top right) → **New repository**.
2. Name it `groweasy-csv-importer`. Keep it **Public**. Click **Create repository**.
3. On the new repo page, click **"uploading an existing file"**.
4. Drag the entire contents of this project folder (everything inside
   `groweasy-csv-importer/`, i.e. the `backend` folder, `sample_data` folder,
   `README.md`, `.gitignore`) into the upload box.
5. Scroll down, click **Commit changes**.
6. Your repo URL will be: `https://github.com/YOUR-USERNAME/groweasy-csv-importer`
   — copy this, you'll need it for submission.

## Step 4 — Deploy the app on Render (free hosting)

1. Go to https://render.com and sign up (you can sign up with your GitHub account —
   this also makes Step 4.3 easier).
2. Click **New +** → **Web Service**.
3. Connect your GitHub account if asked, then select the `groweasy-csv-importer`
   repo you just created.
4. Fill in the settings:
   - **Name:** `groweasy-csv-importer` (or anything you like)
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
5. Scroll to **Environment Variables** and add:
   - Key: `ANTHROPIC_API_KEY` → Value: *(paste the key from Step 1)*
6. Click **Create Web Service**.
7. Wait 2-5 minutes while Render builds and deploys it. When it's done, you'll see a
   URL at the top like `https://groweasy-csv-importer.onrender.com` — that is your
   **hosted application URL**.

   Note: Render's free tier "sleeps" after 15 minutes of no traffic, and the first
   request after that can take 30-60 seconds to wake up. That's normal for a free
   tier and fine for this assignment.

## Step 5 — Test it

1. Open your Render URL in the browser.
2. Upload the file `sample_data/sample_leads.csv` from this project (or any CSV you
   have) to confirm the full flow works end-to-end: upload → preview → confirm →
   AI-mapped results table.
3. If something breaks, check **Render → your service → Logs** for the error message.

## Step 6 — Submit the assignment

Send an email to **varun@groweasy.ai** including:

- **Hosted application URL:** your Render URL from Step 4
- **GitHub repository URL:** your repo URL from Step 3
- **Position you are applying for:** "Software Developer Intern" or
  "Software Developer (Full-Time)" — whichever applies to you

Deadline: **12 July 2026**.

---

### Troubleshooting

- **"ANTHROPIC_API_KEY is not set" error when importing** → you forgot Step 4.5, or
  typo'd the variable name. It must be exactly `ANTHROPIC_API_KEY`.
- **Build fails on Render** → double check "Root Directory" is set to `backend`.
- **Page loads but looks broken (no styling)** → hard-refresh the page (Ctrl+Shift+R
  / Cmd+Shift+R).
