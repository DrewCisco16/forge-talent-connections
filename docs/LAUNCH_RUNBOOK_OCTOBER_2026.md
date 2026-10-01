# 🚀 FORGE Talent Connections: October Launch Runbook

**Who this is for:** Andrew, and anyone helping, with no coding background required.
**What it does:** takes the finished front end and the finished backend code and turns them into one live, tested system, in order, one box at a time.
**How to use it:** work top to bottom. Tick a box only when the "✅ You know it worked when" line is true. Never skip a 🔴 step. If a step fails, stop, and use the 🆘 line on that step.

Legend
- 🔴 **Must do, in order.** Everything after depends on it.
- 🟡 **Do this week, order flexible.**
- 🟢 **Nice to have.** Skip if time is short; come back later.
- ⏱️ Rough time for one sitting.
- 💰 Costs money, or turns on something that can.
- 🔒 Touches a secret. Never paste a secret into chat, email, or a document.
- 🧪 A check you run to prove the step worked.

Where things live
- **App code (front end):** the forge-talent-connections repository on GitHub. The live demo publishes from its `main` branch to www.forgetalentconnections.com/demo/.
- **Backend code:** the `forge-backend` folder delivered with this runbook. It gets its own GitHub repository in Week 1.
- **Google Cloud:** console.cloud.google.com, signed in as andrew@forgetalentconnections.com.
- **Cloudflare:** dash.cloudflare.com, for the domain and the Pages site.

Progress at a glance
- [ ] 🏁 Week 1 done: backend runs on your laptop and in the cloud
- [ ] 🏁 Week 2 done: the app reads the cloud backend; sign-in works
- [ ] 🏁 Week 3 done: testers are in, feedback is flowing
- [ ] 🏁 Week 4 done: fixes shipped, launch plan for 2027 written

---

## 🗓️ Week 1 (Oct 1 to 7): The backend exists, locally and in the cloud

### Day 1: Set up your laptop ⏱️ 60 to 90 minutes

- [ ] 🔴 **1.1 Install Python 3.12.** Go to python.org, Downloads, pick the 3.12 installer for Windows, run it, and tick "Add python.exe to PATH" on the first screen.
  🧪 Open a new terminal (search "Terminal" or "PowerShell") and type `python --version`. ✅ You know it worked when it prints `Python 3.12.x`.
  🆘 If it says "not recognized", re-run the installer and tick the PATH box.

- [ ] 🔴 **1.2 Install Git.** git-scm.com, Download for Windows, run it with every default.
  🧪 `git --version` prints a version. ✅

- [ ] 🔴 **1.3 Install the Google Cloud CLI.** cloud.google.com/sdk/docs/install, Windows installer, run it, let it open a browser and sign in as andrew@forgetalentconnections.com.
  🧪 `gcloud --version` prints versions. ✅

- [ ] 🔴 **1.4 Unzip the backend.** Put the `forge-backend` folder somewhere simple, like `C:\forge\forge-backend`. Do not put it inside the app's folder.
  🧪 You can see `app`, `seed`, `tests`, `deploy.sh`, `README.md` inside it. ✅

- [ ] 🔴 **1.5 Run the backend on your laptop.** In the terminal:
  ```
  cd C:\forge\forge-backend
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements-dev.txt
  set FORGE_CLIENT_SECRET=local-dev-secret
  python -m pytest -q
  uvicorn app.main:app --port 8080
  ```
  🧪 The test line says `36 passed` (or more) and the last line says `Uvicorn running on http://127.0.0.1:8080`. Open http://127.0.0.1:8080/health in a browser. ✅ You know it worked when you see `"status":"ok"`.
  🆘 If `pip install` fails on a Google library, run it again; it is a large download. If it still fails, tell me the last three lines.

- [ ] 🟡 **1.6 Look at your data.** Open http://127.0.0.1:8080/api/v1/profile and http://127.0.0.1:8080/api/v1/opportunities. ✅ You see Drew's profile and the three sample projects, the same ones the demo shows. This is the seed; it is what every new tester will see first.

### Day 2: Create the backend's home on GitHub ⏱️ 20 minutes

- [ ] 🔴 **1.7 Create a private repository** at github.com/new named `forge-talent-backend`. Private. No README (the folder has one). 
- [ ] 🔴 **1.8 Push the folder to it.** In the terminal, inside `forge-backend`:
  ```
  git init
  git add .
  git commit -m "feat: FORGE Talent Connections API, first version"
  git branch -M main
  git remote add origin https://github.com/DrewCisco16/forge-talent-backend.git
  git push -u origin main
  ```
  🧪 Refresh the GitHub page. ✅ You see the files. 🔒 Check that no `.env` file was uploaded (the `.gitignore` prevents it).
- [ ] 🟢 **1.9 Add the repository to our session** so I can push fixes directly: in this chat, say "add the forge-talent-backend repository".

### Day 3: Create the Google Cloud project ⏱️ 45 minutes 💰

- [ ] 🔴 **1.10 Create the project.** console.cloud.google.com, the project picker at the top, New Project, name `forge-talent-connections`, Create. Note the **Project ID** it shows (it may have numbers on the end). Write it here: `________________`
- [ ] 🔴 **1.11 Attach billing.** Billing in the left menu, Link a billing account. 💰 Cloud Run, Firestore, and Vertex AI all have free tiers; a tester program of 20 to 50 people should stay in the low tens of dollars a month. Set a budget alert at 50 dollars: Billing, Budgets and alerts, Create budget.
- [ ] 🔴 **1.12 Create Firestore.** Search "Firestore" in the top bar, Create database, choose **Native mode**, location `us-central1` (or the region closest to Miami: `us-east1`). Create. ✅ You see an empty database page.
- [ ] 🔴 **1.13 Turn on Vertex AI.** Search "Vertex AI", click Enable all recommended APIs. ✅ The Vertex AI dashboard loads with no "enable" button left.
- [ ] 🔴 🔒 **1.14 Create the client secret.** In the terminal:
  ```
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
  Copy the long string it prints. Search "Secret Manager", Create secret, name `forge-client-secret`, paste the string as the value, Create. Then **close the terminal** so the string is gone from the screen. Never save it anywhere else.

### Day 4: Deploy to Cloud Run ⏱️ 30 minutes (first time), then 5 minutes

- [ ] 🔴 **1.15 Sign the CLI in to the project.**
  ```
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```
- [ ] 🔴 **1.16 Deploy.** Inside the `forge-backend` folder:
  ```
  bash deploy.sh
  ```
  (On Windows, if `bash` is missing, open "Git Bash" from the Start menu and run the same command there, with `PROJECT_ID=YOUR_PROJECT_ID REGION=us-central1 ./deploy.sh`.)
  The first run takes several minutes: it enables APIs, creates a service account, builds the container, and deploys it. At the end it prints a **Service URL** like `https://forge-api-xxxxx-uc.a.run.app`. Write it here: `________________`
  🧪 Open `YOUR_SERVICE_URL/health`. ✅ You see `"status":"ok"` and both dependencies `true`.
  🆘 If health says `"store": false`, Firestore was not created in Native mode or in a different project; redo 1.12. If it says `"assistant": false`, Vertex AI is not enabled; redo 1.13.
- [ ] 🔴 **1.17 Prove the data is in the cloud.** Open `YOUR_SERVICE_URL/api/v1/profile`. ✅ Drew's profile, served from Firestore. Open Firestore in the console. ✅ A `people` collection exists with one document, `demo-user`, and a `records` subcollection.

### Day 5: Give the API a proper address ⏱️ 30 minutes

- [ ] 🔴 **1.18 Map a domain.** In Cloud Run, open `forge-api`, Manage custom domains (or "Domain mappings"), Add mapping, enter `api.forgetalentconnections.com`. It shows a DNS record to add.
- [ ] 🔴 **1.19 Add that record in Cloudflare.** dash.cloudflare.com, forgetalentconnections.com, DNS, Add record, exactly as Cloud Run showed it, with the orange cloud **off** (DNS only) for this record.
  🧪 After 10 to 30 minutes, open https://api.forgetalentconnections.com/health. ✅ `"status":"ok"`.
  🆘 If Cloud Run says "certificate pending" for more than an hour, the record is wrong or proxied; check the orange cloud is grey.
- [ ] 🏁 **Week 1 done.** Tick the box at the top.

---

## 🗓️ Week 2 (Oct 8 to 14): The app reads the cloud, and people can sign in

### Connect the front end ⏱️ 15 minutes (I do most of it)

- [ ] 🔴 **2.1 Tell me the API address** in this chat: "The API is at https://api.forgetalentconnections.com". I rebuild the web app with that address compiled in, run every test, and merge. The demo then reads your cloud backend, and its dashboard shows "Live backend connected".
  🧪 Open www.forgetalentconnections.com/demo/ in a private window. ✅ The dashboard banner says "Live backend connected".
- [ ] 🔴 **2.2 Allow the website to call the API.** In Cloud Run, forge-api, Edit and deploy new revision, Variables, set `FORGE_ALLOWED_ORIGINS` to `https://www.forgetalentconnections.com,https://forge-talent-connections.pages.dev`. Deploy.
  🧪 Reload the demo; the Opportunities screen lists the three projects. ✅ If it shows "could not reach the service", the origins list has a typo.

### Sign-in for testers ⏱️ 60 minutes

- [ ] 🔴 **2.3 Create Firebase Authentication.** console.firebase.google.com, Add project, pick the **existing** Google Cloud project `forge-talent-connections`. Build, Authentication, Get started, enable **Email/Password** and **Google** sign-in.
- [ ] 🔴 **2.4 Switch the API to require sign-in.** Cloud Run, forge-api, Edit and deploy new revision, Variables: `FORGE_AUTH` = `firebase`. Deploy.
  🧪 Open `https://api.forgetalentconnections.com/api/v1/profile`. ✅ You now get a polite denial: `"code":"SIGN_IN_REQUIRED"`. That is correct: strangers cannot read records.
- [ ] 🔴 **2.5 Tell me sign-in is on.** I add the sign-in screen's real button (email link and Google) to the app, send the person's token with every request, and merge. ⏱️ One working day on my side.
  🧪 Sign in on the demo with your own email. ✅ Your dashboard loads with the sample record under your name's account.

### Writes, carefully 🔒

- [ ] 🔴 **2.6 Turn record changes on, with the rules.** The backend carries its own governance: two accountable humans open a gate, nobody vouches for themselves or twice, applying and submitting are always pending until a named reviewer decides, every change writes a ledger entry, and denials change nothing. It is switched on by `FORGE_WRITES=local` (the deploy script sets it). What you must add is the reviewer list: Cloud Run, forge-api, Edit and deploy new revision, Variables, `FORGE_REVIEWERS` = the comma-separated user ids of the people allowed to decide (your own id, and one colleague's). With sign-in on, a user id is the Firebase uid shown under Authentication, Users.
  🧪 In the app, submit a piece of work. ✅ It shows as pending, not verified. Then, signed in as a reviewer, verify it. ✅ It flips to verified and the notification names the reviewer. 🔒 Only people in the reviewer list can decide anything; keep that list to two or three names in October.
  🟢 The separate governance service, if and when it is deployed, plugs in through `FORGE_GOVERNANCE_URL` without changing anything above.
- [ ] 🟡 **2.7 Turn the assistant on.** It is already `vertex` in the deploy script. 🧪 In the app, open AI Assistant, ask "What is in my record?" ✅ A short answer grounded in the sample record, ending with the two-human line. 💰 Each question costs a fraction of a cent; the budget alert from 1.11 covers surprises.
- [ ] 🏁 **Week 2 done.**

---

## 🗓️ Week 3 (Oct 15 to 21): Real people use it

### Choose and invite testers ⏱️ 2 hours

- [ ] 🔴 **3.1 Pick 10 to 20 people.** A mix: students, a Veteran or two, one institution contact, one sponsor-type person. Write their names in a private sheet with columns: name, email, phone type, role (Talent, Opportunity, Institution, Veteran), date invited, feedback received.
- [ ] 🔴 **3.2 Write the one-page tester brief** (I will draft it when you say go): what the product is, what to try, the two rules (sample data; nothing you do changes a real record), how to send feedback, and the AI disclosure.
- [ ] 🔴 **3.3 Send invitations** by email from info@forgetalentconnections.com with the demo link and the brief. iPhone users: the home-screen install steps from `docs/IPHONE_DEMO.md`.
- [ ] 🟡 **3.4 Collect feedback in one place.** A Google Form with five questions: what did you try, what confused you, what felt trustworthy, what felt wrong, would you invite a friend. Link it from the brief.

### Watch it run ⏱️ 15 minutes a day

- [ ] 🔴 **3.5 Daily health check.** Open `https://api.forgetalentconnections.com/health` and the demo. ✅ Both fine. If not, Cloud Run, Logs, read the newest red lines, and paste them to me.
- [ ] 🟡 **3.6 Daily cost check.** Billing, Reports. ✅ Flat and small.
- [ ] 🟡 **3.7 Daily feedback triage.** Read new form answers, tag each as bug, confusion, idea, or praise, and send me the bugs and confusions each evening. I fix and merge; you re-test the next morning.
- [ ] 🏁 **Week 3 done.**

---

## 🗓️ Week 4 (Oct 22 to 31): Fix, harden, and set the 2027 course

- [ ] 🔴 **4.1 Fix every bug testers found.** One pull request per bug, tests included, merged by you after a two-minute re-test.
- [ ] 🔴 **4.2 Run the pre-launch checks** on a phone: airplane mode shows honest denials, not blank screens; text at 200 percent still fits; the pitch video plays; every AI surface shows "Before You Use This".
- [ ] 🔴 🔒 **4.3 Rotate the client secret** once testers are done for the month: Secret Manager, forge-client-secret, New version; then redeploy the API. Old versions are disabled automatically on the next deploy.
- [ ] 🟡 **4.4 Back up Firestore.** Firestore, Import/Export, Export to a bucket, once. 💰 Pennies.
- [ ] 🟡 **4.5 Write the November list** from the feedback: the three things testers wanted most, the three confusions to remove, and the one feature to cut.
- [ ] 🔴 **4.6 Decide the launch gate for 2027.** The product launches when all five are true: (1) two-human vouching works end to end with real people, (2) the governance service is deployed and every record change passes through it, (3) counsel has signed off on the rewards program and the Veteran data handling, (4) a hundred tester sessions have run with no silent failure, (5) one outside reviewer has used it cold and could explain it back. Write the date you believe each will be true.
- [ ] 🏁 **Week 4 done.** October complete.

---

## 🆘 If something breaks

- The demo shows the old version: open it in a private window; if still old, Cloudflare, Caching, Purge Everything.
- `/health` is not ok: Cloud Run, forge-api, Logs. Paste the newest red lines to me.
- A screen says "could not reach the service": check `FORGE_ALLOWED_ORIGINS` (2.2) and that the API address in the app matches the mapped domain (1.18).
- Sign-in loops: Firebase Authentication, Settings, Authorized domains must include `www.forgetalentconnections.com`.
- Anything with a secret: never paste it. Create a new version in Secret Manager and redeploy; tell me you rotated it.

## 🧠 ADHD and OCD notes, from me to you

- One box at a time. The order is the plan; you never have to decide what is next.
- Each box has one proof line. If the proof is true, it is done, even if it felt messy.
- If a step takes more than twice its ⏱️ estimate, stop and message me the step number. That is the system working, not you failing.
- The 🟢 boxes are allowed to stay empty in October.
