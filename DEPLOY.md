# Thread DB Master Builder — Deployment Guide

## 1. Push to GitHub

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/thread-db-master-builder.git
git branch -M main
git push -u origin main
```

## 2. Deploy on Streamlit Cloud

1. Go to https://streamlit.io/cloud and sign in with GitHub.
2. Click **"New app"**.
3. Select your repository, branch `main`, and set **Main file path** to:
   `app.py`
4. Click **"Deploy"**.

## 3. Configure Secrets (Optional)

If you need to set a default folder or API keys, use Streamlit Cloud **Settings > Secrets**:

```toml
[main_folder]
path = "/mount/src/thread-db-master-builder/THREAD DB FOR FORECAST"
```

> Note: Streamlit Cloud runs in a Linux container. Use Linux-style paths.
> The app currently reads from a local folder path entered in the sidebar.

## 4. File Structure

```
thread-db-master-builder/
├── app.py                 # Main Streamlit app
├── run_app.py            # Local launcher (headless, port 8503)
├── requirements.txt      # Python dependencies
├── .gitignore           # Excludes data, caches, debug files
└── DEPLOY.md            # This file
```

## 5. Local Run

```bash
python -m streamlit run app.py --server.port 8503 --server.headless true
```

## 6. Notes

- **Do not** commit Excel files or data folders; `.gitignore` excludes `*.xlsx`.
- Streamlit Cloud free tier has 1 GB RAM and sleeps after inactivity.
- For large datasets, consider adding a file uploader widget instead of folder scanning.
