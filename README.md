# Term Hunter

A Windows desktop app that stays open in the background, checks news sites
every 20-60 minutes, and lists **newly coined AI & science words** together
with **ready-made domain name ideas** (`word.ai`, `getword.com`, `theword.tech` ...).

| New word | Suggested domains | Source | Discovered |
|---|---|---|---|
| brain rot | ✓ brainrot.ai  ✗ brainrot.com ... | BBC Technology | 2026-10-12 14:03:11 |

`✓` = the name did not resolve (probably free), `✗` = already in use.

---

## Quick start (3 steps)

### Step 1 - Python (usually automatic)
`run.bat` installs Python for you on Windows 10/11 (via the built-in `winget`). If that ever fails, install it by hand:
1. Go to **https://www.python.org/downloads/** and click the big yellow **Download** button.
2. Open the installer. **Tick the box "Add python.exe to PATH"** at the bottom of the first screen, then click **Install Now**.

> Already have Python 3.10 or newer? Skip to step 2.

### Step 2 - Get the app
Unzip the `TermHunter` folder anywhere (e.g. your Desktop). Right-click the zip -> **Extract All...**

### Step 3 - Double-click `run.bat`
* The first time, a black window installs what the app needs (1-2 minutes, internet required).
* Then the **Term Hunter** window opens. Click **▶ Start**. That's it!

Next time, just double-click `run.bat` again - it opens instantly.
(If Windows shows "Windows protected your PC", click **More info -> Run anyway**.)

---

## Using the app
* **▶ Start / ■ Stop** - begin or end automatic checking. A check runs right away on Start.
* **Search now** - run one check immediately.
* **Check every** slider - 20 to 60 minutes (a little random variation is added on purpose).
* **Filter box** - type to filter the table. Click a column heading to sort.
* **Double-click a row** - opens the news article where the word was found.
* **Right-click a row** - copy the term, copy domains, or check the name on Namecheap.
* **Export CSV** - opens in Excel. **Clear all** - empties the list.
* Options: *check if domains look free*, *hide to tray when closed* (the app keeps running
  next to the clock - right-click the tray icon to quit), *start automatically on launch*.

Your results are saved automatically - close and reopen any time.

**Run at Windows startup (optional):** press `Win + R`, type `shell:startup`, Enter, and drop a
shortcut to `run.bat` in that folder. Tick "Start automatically on launch" in the app too.

---

## Get a true no-Python `TermHunter.exe` (zero install)
A Windows .exe must be built on Windows. Free, no-install way: upload this folder to a GitHub repository,
open its **Actions** tab, run **Build Windows exe**, and download the `TermHunter-Windows` file it makes.
Zip that `.exe` and share it - others just unzip and double-click.
Or, on any Windows PC, use `build_exe.bat` below.

## Optional: make a single `TermHunter.exe`
Double-click **`build_exe.bat`** (takes a few minutes). You get `dist\TermHunter.exe`, which
runs on any Windows PC with no Python. Windows may warn about unsigned apps; choose *Run anyway*.

---

## How it finds words
1. **Cue phrases** - headlines/summaries such as *coined the term "X"*, *dubbed "X"*, *so-called "X"*.
2. **Rare words** - words missing from a large English frequency list (so likely new), with people/company names filtered out.

Expect some noise: no automatic method is perfect. Cue-phrase finds are usually the best.

**Sources** (RSS feeds, edit `sources.py` to add/remove): Google News searches & topics, BBC, NY Times,
The Guardian, MIT Technology Review, Wired, Ars Technica, TechCrunch, VentureBeat, The Verge, Nature,
Science, ScienceDaily, Phys.org, arXiv cs.AI.

**Being polite to websites:** one request at a time, 1-2.5 s pauses, only public RSS feeds,
unchanged feeds are skipped, and a site that says "slow down" is left alone for an hour.

**Important:** the "✓ likely free" mark is only a quick DNS hint. Always confirm at a registrar
before buying, and check that the word isn't someone's trademark.

---

## Troubleshooting
| Problem | Fix |
|---|---|
| "Python is not installed" | Do step 1; make sure you ticked **Add python.exe to PATH**. If you installed it from the Microsoft Store, install the python.org version instead. |
| Setup fails | Check internet, delete the `.venv` folder, double-click `run.bat` again. |
| Nothing found yet | Click **Search now** and wait ~1 minute; all feeds are visited one by one. |
| Window vanished | It's in the system tray (bottom-right, maybe under the `^`). Double-click the icon. |
| Need logs | `%APPDATA%\TermHunter\termhunter.log` |

Data folder: `%APPDATA%\TermHunter\` (delete it to reset everything).

## Files
`app.py` window - `monitor.py` background checker - `extractor.py` word detection -
`domains.py` domain ideas - `sources.py` feed list - `storage.py` saving - `run.bat` launcher
