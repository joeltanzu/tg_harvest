# tg_harvest

> Extract visible contact numbers from your Telegram groups, channels, and DMs — all in one clean desktop app.

![version](https://img.shields.io/badge/version-1.1-00d4aa?style=flat-square)
![platform](https://img.shields.io/badge/platform-macOS-lightgrey?style=flat-square)
![python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)

---

## What it does

Telegram doesn't give you an easy way to see all the contact numbers floating around your chats. `tg_harvest` scans every group, channel, and DM you're in, collects all visible phone numbers, and exports them into a clean CSV or JSON file — with metadata like last seen, mutual contact status, and Premium badge.

---

## Features

- 🔍 Scans all groups, channels, and DMs automatically
- 📱 Extracts visible phone numbers (respects Telegram's privacy settings)
- 🕐 Shows last seen status for each contact
- 🤝 Flags mutual contacts vs unsaved contacts
- ★ Identifies Telegram Premium users
- 🎛️ Export filters — phone numbers only, or unsaved contacts only
- 💾 Export to CSV or JSON, saved directly to your Desktop
- 🔐 Credentials stored locally, never leave your machine

---

## Requirements

- Python 3.9+
- A Telegram account
- API credentials from [my.telegram.org](https://my.telegram.org)

---

## Getting Started

### 1. Get your Telegram API credentials

1. Go to [my.telegram.org](https://my.telegram.org) and log in
2. Click **API Development Tools**
3. Create a new app — fill in any name and description
4. Copy your **API ID** and **API Hash**

### 2. Install dependencies

```bash
pip3 install telethon pywebview
```

### 3. Run the app

```bash
python3 main.py
```

Enter your API ID, API Hash, and phone number on first launch. Credentials are saved locally so you only need to do this once.

---

## Export Fields

| Field | Description |
|---|---|
| `first_name` | Contact's first name |
| `last_name` | Contact's last name |
| `username` | Telegram @username |
| `phone` | Phone number (if visible) |
| `last_seen` | Online / Recently / Last week / Last month / Date |
| `is_mutual` | Whether they have you saved too |
| `is_premium` | Whether they're a Telegram Premium subscriber |
| `source_group` | Which chat they were found in |

---

## Export Filters

On the results screen you can optionally filter before exporting:

- **Has visible phone number** — only include contacts where a number was found
- **Unsaved contacts** — only show people who haven't saved you back (the ones worth adding)

Both filters are off by default so you always see the full raw data first.

---

## Privacy & Security

- All processing happens **locally on your machine**
- No data is sent to any server — only direct communication with Telegram's official API via Telethon
- Phone numbers are only visible for users who have set their Telegram privacy to **Everyone** or **My Contacts**

To revoke access, use the **Clear Credentials** button in the app, or go to **Telegram Settings → Devices** and terminate the session manually.

---

## Notes

- Large public channels may restrict member listing — these will show up as "groups without contact access" in the summary
- Bio fetching is disabled to keep scans fast
- Bots are automatically excluded from results

---

## Built With

- [Telethon](https://github.com/LonamiWebs/Telethon) — Telegram MTProto API client
- [pywebview](https://pywebview.flowrl.com/) — Native desktop window with web UI
- Vanilla HTML/CSS/JS — no frontend frameworks

---

## License

MIT — do whatever you want with it, just don't be weird about it 🙂
