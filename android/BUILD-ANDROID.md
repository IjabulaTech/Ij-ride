# Publishing IJ Ride to the Google Play Store (Android / TWA)

IJ Ride is a PWA. To put it on Play we wrap `ijrides.com` in a **TWA** (Trusted
Web Activity) — a thin native shell that shows your real website full-screen,
with no browser address bar. Users get the exact same app, installed from Play.

Everything the wrapper needs is already in this repo:
- Web manifest: `https://ijrides.com/manifest.webmanifest` (name, icons, colours)
- Icons incl. 512×512 + maskable: `frontend/public/icons/`
- Digital Asset Links file: `frontend/public/.well-known/assetlinks.json`
- Bubblewrap config (for the CLI path): `android/twa-manifest.json`

> **App ID (permanent, choose once):** `com.ijrides.app`
> This can never change after your first upload. It's already set in the files above.

---

## One-time setup you need first
1. **Google Play Developer account** — one-time **US $25** at
   <https://play.google.com/console/signup>. Approval can take a day or two.
2. **A privacy policy URL** — already live: **https://ijrides.com/privacy**
3. **Make sure ijrides.com is deployed and working** (it is).

---

## The easy path (recommended — no software to install): PWABuilder
This produces a ready-to-upload `.aab` file in your browser.

1. Go to **<https://www.pwabuilder.com>**.
2. Enter **`https://ijrides.com`** and click **Start**. It will analyse the PWA
   (it should score well — manifest, icons and service worker are all present).
3. Click **Package for stores → Android → Generate Package**.
4. In the Android options, set:
   - **Package ID:** `com.ijrides.app`
   - **App name:** `IJ Ride`
   - **Signing key:** choose **"Create new"** (PWABuilder makes and keeps it for
     you — **download and keep the `signing.keystore` + passwords safe**; you'll
     need the same key for every future update).
5. **Download** the zip. Inside you get:
   - `app-release-signed.aab` ← this is what you upload to Play
   - `assetlinks.json` ← contains your app's SHA-256 fingerprint
   - a `README` / `next-steps` file.
6. **Finish Digital Asset Links** (removes the browser bar):
   - Open the `assetlinks.json` from the zip, copy the **`sha256_cert_fingerprints`**
     value.
   - Paste it into `frontend/public/.well-known/assetlinks.json` in this repo,
     replacing `REPLACE_WITH_SHA256_FINGERPRINT_FROM_PLAY_CONSOLE_APP_SIGNING`.
   - Commit & push so it goes live at
     **https://ijrides.com/.well-known/assetlinks.json**.
   - ⚠️ If you use **Play App Signing** (recommended, and on by default), Google
     re-signs the app with its own key. After your first upload, go to
     **Play Console → your app → Setup → App signing** and copy the
     **"SHA-256 certificate fingerprint"** shown there — use *that* one in
     `assetlinks.json` (and you can include both). This is the #1 reason the
     address bar sometimes stays visible.

Then jump to **"Upload to Play"** below.

---

## The developer path (optional): Bubblewrap CLI
Use this only if you prefer the command line. It needs a **JDK 17** and the
**Android SDK** (Bubblewrap can download them for you on first run).

```bash
npm install -g @bubblewrap/cli
cd android
bubblewrap init --manifest=https://ijrides.com/manifest.webmanifest
# accept the defaults; a twa-manifest.json like the one in this folder is created,
# and a signing keystore is generated — BACK IT UP.
bubblewrap build
```

This outputs `app-release-signed.aab`. Get your signing fingerprint with:

```bash
bubblewrap fingerprint list
```

…and put its SHA-256 into `frontend/public/.well-known/assetlinks.json`
(same rule about Play App Signing as above).

---

## Upload to Play
1. **Play Console → Create app** → name **IJ Ride**, type **App**, **Free**.
2. **Create a release** (start with **Internal testing** to try it on your own
   phone first, then promote to Production).
3. **Upload** `app-release-signed.aab`.
4. Fill the required listing (see checklist below) and submit for review.
   First review typically takes a few hours to a couple of days.

---

## Play listing checklist (all required before you can publish)
- **App icon** 512×512 (you have it: `icon-512.png`).
- **Feature graphic** 1024×500 (a banner — can be made from the logo; ask me).
- **Screenshots:** at least 2 phone screenshots (take them from the live app).
- **Short description** (≤80 chars) and **Full description**.
- **Privacy Policy URL:** `https://ijrides.com/privacy` ✅ (already live).
- **Data safety form:** declare what you collect — **Location**, **Personal info**
  (name, phone, email), **Photos**, **App activity**. Say it's used for app
  functionality, not sold. (Matches the privacy policy.)
- **App access:** since sign-in is required, give Google a **test login**
  (a test passenger phone + password) so reviewers can get in.
- **Content rating** questionnaire, **Target audience** (18+), **Ads** (none).

---

## After you publish
- **Updating the app later:** most changes are just website changes — you deploy
  the web app as usual and users get them instantly, **no new Play upload needed**.
  You only rebuild & re-upload the `.aab` to change the icon, name, Android
  version, or TWA settings — and you must sign it with the **same key** you saved.
- Keep your **signing keystore + passwords** backed up forever. Losing them means
  you can't update the app.

Questions on any step — tell me which one and I'll walk you through it.
