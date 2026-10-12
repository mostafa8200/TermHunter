# Term Hunter 2.0 - domain opportunity radar

A Windows desktop app that stays open in the background, checks news sites every
20-60 minutes, finds **newly coined words** in the sectors you choose, and builds
**domain ideas** for each one - with a **premium score** so the best words rise to the top.

## Quick start
**Easiest:** if you have `TermHunter.exe`, just double-click it. Nothing to install.

**From this folder:** double-click **`run.bat`**. First time only, it installs Python (if missing)
and the app's libraries (a few minutes, internet needed). After that it opens instantly.
(If Windows says "protected your PC": **More info -> Run anyway**.)

Then click **▶ Start monitoring**. That's it.

## What's new in 2.0
* **Premium design** - sidebar + dashboard with stat cards, **Dark / Light / System** themes (bottom of the sidebar).
* **Sectors** - tick what you care about: AI, Science, Medicine, Biotech, Finance, Crypto & Web3,
  Technology, Robotics, Cybersecurity, Space, Energy & Climate. Only matching feeds and Google News
  searches are used, and every word is tagged with its sector.
* **One column per domain extension** - `.com .ai .io .tech .app .dev .co .si` by default.
  Open **⚙ Settings -> Domains** to choose from 50+ extensions (including **.si**), or add your own (e.g. `co.uk`).
* **Name styles** - exact word plus `getword`, `theword`, `tryword`, `myword`, `useword`, `wordhq`, `wordlabs`, `wordai`, `wordapp`.
* **Premium score (0-100)** - rewards short, one-word, pronounceable, clean names, valuable sectors, and a free .com/.ai/.io/.co.
  Rows scoring 75+ show in **gold**. Use the **Min score** slider to hide the rest.
* **Best pick** column, **Other ideas** column, **favorites (★)**, search box, sector filter, sortable columns, re-check, delete, CSV export.

## Table columns
Term - Sector - Score - Best pick - *one column per extension* - Other ideas - Source - Date & time discovered.
`✓` = looks free (does not resolve), `✗` = already in use.

## Tips
* **Double-click** a row to open the article. **Right-click** for favorite, copy, Namecheap/GoDaddy check, re-check, delete.
* Click a column heading to sort (click again to reverse). Scroll sideways if you chose many extensions.
* Closing the window hides the app to the system tray (turn off in Settings). Right-click the tray icon to quit.
* Run at Windows startup: press `Win + R`, type `shell:startup`, and drop a shortcut to the app there; enable
  "Start monitoring automatically" in Settings.

## How words are found
1. **Cue phrases** - *coined the term "X"*, *dubbed "X"*, *so-called "X"* in headlines and summaries.
2. **Rare words** - words missing from a big English frequency list (names of people/companies are filtered). Can be switched off in Settings -> Search.

Expect some noise; no automatic method is perfect.

**Polite to websites:** one request at a time, 1-2.5 s pauses, public RSS feeds only, unchanged feeds skipped,
a site that says "slow down" is left alone for an hour. Edit `sources.py` / `sectors.py` to add feeds or keywords.

**Important:** "✓ looks free" is only a quick DNS hint. Always confirm at a registrar and check trademarks before buying.
Checking many extensions means more lookups per word; reduce the extensions or turn the check off if it feels slow.

## Build your own TermHunter.exe (no Python needed to run it)
* **Free, no install:** upload this folder to a GitHub repository -> **Actions** -> **Build Windows exe** -> **Run workflow**
  -> download **TermHunter-Windows**. (The file `.github/workflows/build.yml` does the work.)
* **Or on any Windows PC:** double-click `build_exe.bat` -> `dist\TermHunter.exe`.

## Troubleshooting
| Problem | Fix |
|---|---|
| Setup fails | Check internet, delete the `.venv` folder, run `run.bat` again. |
| Nothing found yet | Click **Search now** and wait about a minute while every feed is visited. |
| Window vanished | It is in the system tray (bottom-right, maybe under the `^`). |
| Few results | Tick more sectors, enable rare-word detection, or lower **Min score**. |
| Logs | `%APPDATA%\TermHunter\termhunter.log` (data is in the same folder) |

## Files
`app.py` window - `monitor.py` background checker - `extractor.py` word detection - `sectors.py` sectors & keywords -
`sources.py` feeds - `domains.py` domain ideas & score - `storage.py` saving - `run.bat` / `build_exe.bat` launchers
