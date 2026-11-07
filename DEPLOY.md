# Put TicketDesk online — step by step

**Goal:** a public website link (your live demo) and a GitHub link, both for your resume.
**Cost:** ₹0. **Time:** about 1–1.5 hours the first time.
**You do NOT need Docker, Python or Node installed for this.** The hosting sites build everything for you.

Four services, each with one job:

| Service | Job | What it gives you |
|---|---|---|
| GitHub | stores your code | the link recruiters open to read your code |
| Neon | stores the database | (internal, nobody sees it) |
| Render | runs the backend API | an API address like `https://ticketdesk-api-xxxx.onrender.com` |
| Vercel | hosts the website | **your live demo link** like `https://ticketdesk.vercel.app` |

Do the parts in order. After each part there is a **Check** line. Do not move on until the check passes.

Keep a Notepad file open while you work. You will copy several values (database string, two website addresses) and paste them later.

---

## Part 1 — Install Git

1. Go to https://git-scm.com/downloads and download the installer for your system.
2. Run it. Click **Next** on every screen and keep all defaults. Click **Install**, then **Finish**.
3. Open a terminal:
   - **Windows:** press the Windows key, type `cmd`, press Enter.
   - **Mac:** press Cmd+Space, type `Terminal`, press Enter.
4. Type this and press Enter:
   ```
   git --version
   ```

**Check:** it prints something like `git version 2.45.0`. If it says "not recognized" or "command not found", close the terminal, open a new one and try again. If it still fails, restart your computer.

5. Tell Git who you are (use your real name and the email you will use for GitHub). Run both lines, one at a time:
   ```
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
   Nothing is printed when it works.

---

## Part 2 — Put your code on GitHub

### 2.1 Create a GitHub account
1. Go to https://github.com and click **Sign up**. Use an email you will keep long term. Pick a professional username (it appears in your link, e.g. `github.com/avi-dev`).
2. Verify your email when GitHub asks.

### 2.2 Create an empty repository
1. Click the **+** at the top right, then **New repository**.
2. **Repository name:** `ticketdesk`
3. Choose **Public**. (Recruiters must be able to open it.)
4. **Leave all three boxes unticked:** "Add a README", "Add .gitignore", "Choose a license". The project already has these. Ticking them causes an error later.
5. Click **Create repository**.

**Check:** you see a page titled with your username and `ticketdesk`, with a box of setup commands. Leave this tab open.

### 2.3 Unzip the project
1. Find `ticketdesk-portfolio.zip` (downloaded from this chat).
2. Right-click it, **Extract All** (Windows) or double-click it (Mac). Put it somewhere easy, like `Documents`.
3. Open the extracted `ticketdesk-portfolio` folder.

**Check:** inside you see `backend`, `frontend`, `Dockerfile`, `docker-compose.yml`, `README.md` and `DEPLOY.md` directly. If you only see one more folder named `ticketdesk-portfolio`, open that one: the folder you want is the one that contains `backend` and `frontend`.

### 2.4 Open a terminal inside that folder
- **Windows:** with the folder open in File Explorer, click the address bar at the top, type `cmd`, press Enter. A terminal opens already inside the folder.
- **Mac:** open Terminal, type `cd ` (with a space), drag the folder from Finder into the Terminal window, press Enter.

Run `dir` (Windows) or `ls` (Mac).

**Check:** the list shows `backend`, `frontend`, `Dockerfile`.

### 2.5 Push the code
Run these one at a time. Replace `YOUR_USERNAME` with your GitHub username in the 4th command.
```
git init
git add .
git commit -m "Initial commit: TicketDesk"
git remote add origin https://github.com/YOUR_USERNAME/ticketdesk.git
git branch -M main
git push -u origin main
```
What you will see:
- After `git commit`: a long list of "create mode ..." lines. Good.
- During `git push`: a browser window or popup asks you to sign in to GitHub. Click **Sign in with your browser** and approve. If asked for a password in the terminal instead, GitHub does not accept your account password there. Use the browser option, or create a token at https://github.com/settings/tokens (classic, tick `repo`) and paste that as the password.

**Check:** refresh your GitHub repo page. You see the folders and `README.md` listed.

Common errors:
- `remote origin already exists` → run `git remote set-url origin https://github.com/YOUR_USERNAME/ticketdesk.git`, then run the `git push` line again.
- `Author identity unknown` → you skipped Part 1 step 5. Do it, then run the `git commit` line again.
- `src refspec main does not match any` → the commit did not happen. Run `git add .` and the `git commit` line again, then `git push -u origin main`.

---

## Part 3 — Create the database on Neon

1. Go to https://neon.com and click **Sign up**. Use **Continue with GitHub** (easiest).
2. Create a project when asked: name it `ticketdesk`, keep the default Postgres version, and pick the region closest to you (for India, a Singapore region if listed). Click **Create**.
3. In the Neon console, click **Connect**. A box titled **"Connect to your branch"** opens. Leave the defaults selected (branch, database, role).
4. Copy the connection string shown. It looks like:
   ```
   postgresql://someuser:somepassword@ep-something.region.aws.neon.tech/neondb?sslmode=require
   ```
   If the password is hidden, click the show/reveal option first, so what you copy contains the real password.
5. Paste it into your Notepad file and label it `DATABASE_URL`.

**Check:** the string starts with `postgresql://`, contains `@ep-`, and has no `****` in it. **Do not edit it.** The app converts it automatically.

Why Neon and not Render's database: Render's free database is deleted 30 days after creation (this is in Render's docs). Your demo would break.

---

## Part 4 — Run the backend on Render

### 4.1 Sign up and connect GitHub
1. Go to https://render.com and click **Get Started**. Choose **GitHub** to sign in.
2. When Render asks for GitHub access, allow it for your `ticketdesk` repository (or all repositories).

### 4.2 Create the service
1. Click **+ New** (top right), then **Web Service**.
2. Pick your `ticketdesk` repo from the list and click **Connect**. If it is missing, click the link to configure GitHub access and add it.
3. Fill in the form:
   - **Name:** `ticketdesk-api`
   - **Language:** `Docker`
   - **Branch:** `main`
   - **Region:** choose the one closest to your Neon region.
   - **Root Directory:** leave **empty**. The project has a `Dockerfile` at the top level, so no setting is needed.
   - **Instance Type:** `Free`

### 4.3 Add the environment variables
In the **Environment Variables** section, add these five, one at a time (name on the left, value on the right):

| Name | Value |
|---|---|
| `DATABASE_URL` | the Neon string from Part 3 |
| `SECRET_KEY` | a long random string, 40+ characters (see below) |
| `RUN_SEED` | `1` |
| `INLINE_SLA_WORKER` | `1` |
| `CORS_ORIGINS` | `https://example.com` (placeholder, you fix it in Part 6) |

Making `SECRET_KEY`:
- If Python is installed: run `python -c "import secrets; print(secrets.token_hex(32))"` and copy the output.
- Otherwise, use any password generator set to 48 characters, or type a long random string yourself. Never reuse a real password, and never put this value in your code.

What the flags do: `RUN_SEED=1` loads the demo company and tickets on start (safe to repeat, it skips if already there). `INLINE_SLA_WORKER=1` runs the SLA-breach checker inside the API, because Render's free plan does not allow a separate background worker.

### 4.4 Deploy
1. Click **Deploy Web Service**.
2. A log page opens. The first build takes several minutes. Watch for these lines:
   - `Seeded. Org slug 'acme'.` (the database tables were created and the demo data loaded; there is no separate message for the tables, so no red error before this line means they worked)
   - `Uvicorn running on http://0.0.0.0:...`
   - then Render shows **Live**.
3. At the top of the page, copy the service address (it ends in `.onrender.com`). Paste it in Notepad as `API_URL`.

**Check:** open `API_URL/health` in your browser. You see `{"status":"ok"}`. Then open `API_URL/docs`. You see an API page titled "TicketDesk API".

If the deploy fails, scroll to the red error in the log:
- `could not translate host name` or `password authentication failed` → `DATABASE_URL` was pasted wrong. Re-copy it from Neon (Part 3), fix it under **Environment** in Render, save.
- `ModuleNotFoundError` or `No such file` → make sure **Root Directory** is empty and **Language** is Docker.
- Anything else: copy the last 20 log lines and send them to me.

---

## Part 5 — Put the website on Vercel

1. Go to https://vercel.com and click **Sign Up**. Choose **Continue with GitHub**.
2. Click **Add New…**, then **Project**.
3. Find `ticketdesk` in the list and click **Import**. (If it is missing, click the option to adjust GitHub permissions and add the repo.)
4. On the **Configure Project** screen:
   - **Root Directory:** click **Edit**, choose the `frontend` folder, and confirm. This is required. Without it the build fails.
   - **Framework Preset:** it should show **Vite**. Leave the build and output settings as they are.
   - Open **Environment Variables** and add:
     - Name: `VITE_API_URL`
     - Value: your `API_URL` from Part 4, **with no `/` at the end**, e.g. `https://ticketdesk-api-xxxx.onrender.com`
5. Click **Deploy** and wait for the build (1–2 minutes).
6. Click the preview image or **Visit**. Copy the address from your browser (e.g. `https://ticketdesk-xxxx.vercel.app`). Paste it in Notepad as `SITE_URL`.

Note: `VITE_API_URL` is fixed into the site when it is built. If you ever change it, you must redeploy on Vercel (Deployments tab, ⋯ menu, **Redeploy**).

**Check:** the TicketDesk sign-in page appears. Logging in will not work yet. That is fixed next.

---

## Part 6 — Connect the two

1. Go back to Render, open your `ticketdesk-api` service, click **Environment**.
2. Edit `CORS_ORIGINS`: replace `https://example.com` with your `SITE_URL` (the exact address of your Vercel site).
3. Click **Save**. Render redeploys by itself. Wait until it says **Live** again.
4. Open your `SITE_URL` and sign in:
   - **Workspace ID:** `acme`
   - **Email:** `admin@acme.com`
   - **Password:** `demo1234`

**Check:** you see a table of tickets. Click one, change its status, add a reply. Click **Admin** and see the SLA report and users.

Important behaviors on the free plan (from Render's docs):
- After 15 minutes with no visits, the API goes to sleep. The next visit takes **about a minute** to wake up. Before sending your link to anyone, open it once yourself so it is awake.
- Free web services get 750 hours per month, which is enough for one always-on app.

If login says "Failed to fetch" or shows a network error:
1. Wait a minute and retry (the API may be waking up).
2. Check that `CORS_ORIGINS` on Render is exactly your Vercel address, with `https://` and no spaces.
3. Check that `VITE_API_URL` on Vercel is your Render address, redeploy on Vercel if you changed it.
4. Press F12 in the browser, open the **Console** tab, and send me the red message.

---

## Part 7 — Make it recruiter-ready

### 7.1 Edit the README
1. Install **VS Code** from https://code.visualstudio.com if you don't have an editor. Open the `ticketdesk-portfolio` folder in it, then open `README.md`.
2. In the first badge line near the top, replace `YOUR_USERNAME` with your GitHub username.
3. On the `**Live demo:** _add link_` line, replace `_add link_` with your `SITE_URL`. After it, add: `(free hosting: first load can take about a minute to wake up)`.

### 7.2 Add screenshots
1. Open your live site. Take screenshots of the ticket list, a ticket's detail page, and the Admin page.
   - Windows: press Win+Shift+S, drag over the area, then paste into Paint and save. Mac: press Cmd+Shift+4.
2. In your project folder, create a folder named `docs` and save them as `tickets.png`, `detail.png`, `admin.png`.
3. In `README.md`, just under the "Live demo" line, add:
   ```
   ![Ticket list](docs/tickets.png)
   ![Ticket detail](docs/detail.png)
   ![Admin](docs/admin.png)
   ```

### 7.3 Push the changes
In your terminal, inside the project folder:
```
git add .
git commit -m "Add live demo link and screenshots"
git push
```

**Check:** open your GitHub repo. The README shows your screenshots and live link. Then click the **Actions** tab. Within a minute or two you see a run named "Add live demo link and screenshots". It should end with a green tick (it runs the backend tests and builds the frontend). If it shows a red cross, click it, open the failed step, and send me the error.

### 7.4 Use it
- Resume, under Projects:
  **TicketDesk — Multi-tenant support ticketing system** (GitHub link · Live demo link)
  *FastAPI, PostgreSQL, React/TypeScript, Docker, GitHub Actions. JWT auth with role-based access (customer/agent/admin), tenant isolation, SLA tracking with a background checker, full-text search, audit history, 22 automated tests.*
- Pin the repo on your GitHub profile: go to your profile, click **Customize your pins**, tick `ticketdesk`.
- The demo login is public on purpose. Never put a real password in the demo.

---

## Appendix — run it on your own computer (optional)

You don't need this to deploy. Use it only if you want to test locally.

1. Install **Docker Desktop** from https://www.docker.com/products/docker-desktop and open it. Wait until it says it is running. On Windows it may ask to enable WSL 2 or virtualization. Accept, restart if asked.
2. In a terminal inside the project folder run:
   ```
   docker compose up --build
   ```
   The first run takes several minutes. It starts the database, API, SLA worker and website, and loads demo data.
3. Open http://localhost:5173 and sign in with `acme` / `admin@acme.com` / `demo1234`. API docs are at http://localhost:8000/docs.
4. Stop it with Ctrl+C in the terminal.
