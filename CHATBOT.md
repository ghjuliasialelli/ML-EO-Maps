# Website chatbot

The **Chatbot** page of the book (`chatbot.qmd`) embeds a Q&A assistant that answers
questions using only the book's content and links to the relevant pages.

- **Space:** <https://huggingface.co/spaces/ghjuliasialelli/ML-EO-Maps-chatbot> (renamed from `ML-EO-Maps` in Nov 2026)
- **Direct app URL (used in the iframe):** <https://ghjuliasialelli-ml-eo-maps-chatbot.hf.space>
- **Local clone:** `~/Documents/GitHub/ML-EO-Maps-chatbot`
- **Model:** Google Gemini 2.5 Flash, free tier, via the `google-genai` SDK

This page was reconstructed in November 2026 from the Space's commit history and this
repo's git log. Steps marked *likely* are inferred, not recorded.

---

## How it works

- Hugging Face Space, **Gradio** SDK (6.16.0, set in the Space's `README.md`), Python 3.13,
  **CPU basic** (free) hardware, **public**, license `cc-by-nc-4.0`.
- No retrieval / vector database. At startup `app.py` reads every `content/*.qmd`, labels
  each with its live URL (`https://ghjuliasialelli.github.io/ML-EO-Maps/<slug>.html`), and
  puts all of it in the Gemini system prompt (Gemini's large context window makes this work).
- System prompt rules: answer only from the website content, be concise, always cite the
  relevant page URL(s), say so if the content doesn't cover the question, use markdown.
- Temperature 0.2. Rate-limit errors (429 / `RESOURCE_EXHAUSTED`) show a friendly
  "temporarily rate-limited" message instead of crashing.
- UI: `gr.ChatInterface` with five example questions; `cache_examples=False`.

Files in the Space:

```
README.md          # HF Space config header (sdk, sdk_version, app_file, license)
.gitattributes     # auto-generated
app.py             # loads content/, builds prompt, calls Gemini, Gradio UI
requirements.txt   # gradio>=5.0, google-genai>=1.0
content/*.qmd      # manual copy of the book's .qmd pages
```

The API key is stored as the Space secret `GEMINI_API_KEY`
(Space → **Settings → Variables and secrets**). It is never in the code.

---

## How it was set up (5 June 2026, Zurich time)

Everything on the Hugging Face side was done in the **web interface** (no git, no local
clone). The code was written in a Claude chat.

### 1. Get a Gemini API key
<https://aistudio.google.com/apikey> → sign in with a Google account → **Create API key**.
Free tier, no billing.

### 2. Create the Space (11:14)
<https://huggingface.co/new-space>:

| Field | Value |
|---|---|
| Owner / name | `ghjuliasialelli` / `ML-EO-Maps` |
| License | `cc-by-nc-4.0` |
| SDK | **Gradio** (blank template) |
| Hardware | **CPU basic** (free) |
| Visibility | **Public** (required for the iframe embed) |

This creates `README.md` (config header) and `.gitattributes` ("initial commit").
The README has not been edited since.

### 3. Add the API key as a secret
Space → **Settings → Variables and secrets → New secret**: name `GEMINI_API_KEY`, value =
the key from step 1. (Secrets aren't visible in the history, so the exact time is unknown;
the app crashes at startup without it.)

### 4. Upload the code (11:15)
**Files** tab → **+ Add file → Upload files**: `app.py` and `requirements.txt`.

### 5. Upload the book content (11:15)
Upload the book's `.qmd` files (36 at the time) into a `content/` folder, by dragging a local
folder named `content` onto the web uploader (this keeps the folder structure).

### 6. Fix startup errors by editing `app.py` in the browser (11:19, 11:20, 12:34)
The first version targeted Gradio 5 but the Space runs Gradio 6.16.0:
1. Removed `type="messages"` from `gr.ChatInterface` (argument no longer accepted in Gradio 6).
2. Rewrote the history loop to unpack `(user, assistant)` pairs. **This introduced a bug**:
   Gradio 6 still passes history as message dicts, so follow-up questions break. The
   original loop was correct. (Fix prepared in November 2026, see the change log.)
3. Removed `theme=gr.themes.Soft()` (themes are no longer set on `ChatInterface` in Gradio 6).

### 7. Fix model and quota problems (14:26)
- Model `gemini-2.0-flash` → `gemini-2.5-flash` (*likely*: 2.0 Flash errored or had no free quota).
- Wrapped the Gemini call in `try/except` with the rate-limit message.
- Added `cache_examples=False` (*likely*: otherwise Gradio sends every example question to
  Gemini at startup, using up free quota and possibly failing the build).

### 8. Embed it in the book (14:42, 14:45; repo commits `c717f35`, `f70f36b`)
- Created `chatbot.qmd`: heading, one line of intro text, and an
  `<iframe width="100%" height="700" style="border:none; border-radius: 8px;">`.
- Added `chatbot.qmd` to the sidebar in `_quarto.yml`, rendered, pushed.
- **Fix:** the iframe first pointed at `https://huggingface.co/spaces/ghjuliasialelli/ML-EO-Maps`,
  which doesn't work in an iframe. Changed to the direct app URL
  `https://ghjuliasialelli-ml-eo-maps.hf.space` (Space → **⋮ → Embed this Space**).

---

## Updating the chatbot's content

`content/` is **not** synced with this repo. Refresh it after every content update
(e.g. after an Overleaf sync, see `update.md` step 6).

**From the local clone (`~/Documents/GitHub/ML-EO-Maps-chatbot`):**
```sh
cd ~/Documents/GitHub/ML-EO-Maps-chatbot
git pull                                          # pick up any edits made in the web UI
rm content/*.qmd && cp ../ml-eo-maps/*.qmd content/
rm content/chatbot.qmd content/feedback.qmd       # no useful content for the bot
git add -A && git commit -m "Sync book content" && git push
```
`rm content/*.qmd` first means pages renamed or removed from the book also disappear from
the bot. Pushing asks for a password: use a Hugging Face **write** access token
(<https://huggingface.co/settings/tokens>), or run `hf auth login` once. The Space rebuilds
automatically (~1 min); check its **App** tab, then the book's Chatbot page.

If the clone is missing:
`git clone https://huggingface.co/spaces/ghjuliasialelli/ML-EO-Maps-chatbot`

**Web interface (no clone):** Space → **Files** → **+ Add file → Upload files** → drag in a
local folder named `content` holding the `*.qmd` files above → **Commit changes to main**
(same-name files are overwritten). Then delete, one by one, any file in the Space's
`content/` whose page no longer exists in the book.

## Running it locally

```sh
pip install gradio google-genai
export GEMINI_API_KEY="..."
python app.py          # reads ./content by default; override with QMD_DIR=/path/to/qmds
```

## Gotchas

- The Gradio version actually installed is `sdk_version` in the Space's `README.md`
  (6.16.0), not the `>=5.0` in `requirements.txt`. Code written for Gradio 5 may break.
- Gradio 6 passes chat history as `[{"role": "user"|"assistant", "content": ...}, ...]`;
  Gemini calls the assistant role `"model"`.
- The free Gemini tier is rate-limited; occasional "rate-limited" replies under load are expected.
- **Renaming the Space changes the direct app URL** (`<owner>-<space-name>.hf.space`). The
  `huggingface.co/spaces/...` page redirects, but the old `.hf.space` URL returns 404, so
  update the iframe `src` in `chatbot.qmd` after any rename.
- If the API key is revoked or expires, replace the `GEMINI_API_KEY` secret and restart the
  Space (**Settings → Restart Space**).

## Change log

- **2026-06-05:** Space created and embedded in the book (steps above).
- **2026-11-05:** Space renamed `ML-EO-Maps` → `ML-EO-Maps-chatbot` and cloned locally; iframe
  in `chatbot.qmd` updated to the new `.hf.space` URL. Fixed multi-turn history for Gradio 6;
  refreshed `content/` (added the new appendices, `codebase.qmd`, `reference_map.qmd`;
  removed the stale `acknowledgments.qmd`). *(Space commit `24c9ab3`; confirm once pushed.)*
