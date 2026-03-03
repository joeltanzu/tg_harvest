#!/usr/bin/env python3
"""
tg_harvest GUI — Telegram Contact Extractor
Mac desktop app using pywebview + telethon
"""

import webview
import asyncio
import threading
import json
import csv
from pathlib import Path
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
CONFIG_PATH  = Path.home() / ".tg_harvest_config.json"
SESSION_PATH = Path.home() / ".tg_harvest_session"

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f)
    CONFIG_PATH.chmod(0o600)

def parse_last_seen(status):
    try:
        from telethon.tl.types import (
            UserStatusOnline, UserStatusRecently, UserStatusLastWeek,
            UserStatusLastMonth, UserStatusOffline
        )
        if isinstance(status, UserStatusOnline):    return "Online"
        if isinstance(status, UserStatusRecently):  return "Recently"
        if isinstance(status, UserStatusLastWeek):  return "Last week"
        if isinstance(status, UserStatusLastMonth): return "Last month"
        if isinstance(status, UserStatusOffline):
            if status.was_online:
                return status.was_online.strftime("%Y-%m-%d")
            return "Offline"
    except Exception:
        pass
    return "Unknown"

# ── API exposed to JS ─────────────────────────────────────────────────────────
class TelegramAPI:
    def __init__(self):
        self._window  = None
        self._results = []
        self._running = False

    def set_window(self, w):
        self._window = w

    def get_saved_credentials(self):
        c = load_config()
        if c.get("api_id") and c.get("phone"):
            return {"api_id": c["api_id"], "api_hash": c["api_hash"], "phone": c["phone"]}
        return None

    def clear_credentials(self):
        for p in [CONFIG_PATH, SESSION_PATH.with_suffix(".session")]:
            if p.exists(): p.unlink()
        return True

    def start_harvest(self, api_id, api_hash, phone):
        if self._running:
            return {"error": "Already running"}
        save_config({"api_id": api_id, "api_hash": api_hash, "phone": phone})
        self._running = True
        self._results = []
        threading.Thread(
            target=self._run_harvest,
            args=(api_id, api_hash, phone),
            daemon=True
        ).start()
        return {"status": "started"}

    def _run_harvest(self, api_id, api_hash, phone):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._harvest(api_id, api_hash, phone))
        except Exception as e:
            self._emit("error", {"message": str(e)})
        finally:
            self._running = False
            loop.close()

    async def _harvest(self, api_id, api_hash, phone):
        from telethon import TelegramClient
        from telethon.errors import (
            ChatAdminRequiredError, ChannelPrivateError, SessionPasswordNeededError
        )

        self._emit("status", {"message": "Connecting to Telegram..."})
        client = TelegramClient(str(SESSION_PATH), api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            self._emit("need_code", {"phone": phone})
            code = await self._wait_for_code()
            if not code:
                self._emit("error", {"message": "No code received."})
                await client.disconnect()
                return
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                self._emit("need_2fa", {})
                pw = await self._wait_for_2fa()
                if not pw:
                    self._emit("error", {"message": "No 2FA password received."})
                    await client.disconnect()
                    return
                await client.sign_in(password=pw)

        self._emit("status", {"message": "Connected! Loading chats..."})

        # Scan everything — groups, channels, and DMs
        dialogs = await client.get_dialogs()
        total   = len(dialogs)
        self._emit("total", {"count": total})

        results     = []
        seen_ids    = set()
        seen_phones = set()
        skipped     = 0

        for i, dialog in enumerate(dialogs, 1):
            label = dialog.name or "(unnamed)"
            self._emit("progress", {
                "current": i, "total": total,
                "chat": label, "found": len(results)
            })

            try:
                async for user in client.iter_participants(dialog):
                    if user.is_self or user.bot:
                        continue
                    uid = user.id
                    if uid in seen_ids:
                        continue
                    seen_ids.add(uid)

                    phone_num = user.phone or ""
                    if phone_num:
                        if phone_num in seen_phones:
                            continue
                        seen_phones.add(phone_num)

                    last_seen  = parse_last_seen(user.status)
                    is_mutual  = bool(getattr(user, "mutual_contact", False))
                    is_premium = bool(getattr(user, "premium", False))

                    entry = {
                        "first_name"   : user.first_name or "",
                        "last_name"    : user.last_name  or "",
                        "username"     : f"@{user.username}" if user.username else "",
                        "phone"        : phone_num,
                        "last_seen"    : last_seen,
                        "is_mutual"    : is_mutual,
                        "is_premium"   : is_premium,
                        "source_group" : label,
                    }
                    results.append(entry)

                    if phone_num:
                        self._emit("contact_found", entry)

            except (ChatAdminRequiredError, ChannelPrivateError):
                skipped += 1
            except Exception:
                skipped += 1

        await client.disconnect()

        self._results = results
        with_phone   = sum(1 for r in results if r["phone"])
        mutual_count = sum(1 for r in results if r["is_mutual"])

        self._emit("complete", {
            "total"        : len(results),
            "with_phone"   : with_phone,
            "without_phone": len(results) - with_phone,
            "mutual"       : mutual_count,
            "skipped"      : skipped,
        })

    # ── Code / 2FA handshake ─────────────────────────────────────────────────
    _pending_code = None
    _pending_2fa  = None

    def submit_code(self, code):
        TelegramAPI._pending_code = code
        return True

    def submit_2fa(self, pw):
        TelegramAPI._pending_2fa = pw
        return True

    async def _wait_for_code(self, timeout=120):
        import time
        TelegramAPI._pending_code = None
        start = time.time()
        while TelegramAPI._pending_code is None:
            if time.time() - start > timeout: return None
            await asyncio.sleep(0.5)
        return TelegramAPI._pending_code

    async def _wait_for_2fa(self, timeout=120):
        import time
        TelegramAPI._pending_2fa = None
        start = time.time()
        while TelegramAPI._pending_2fa is None:
            if time.time() - start > timeout: return None
            await asyncio.sleep(0.5)
        return TelegramAPI._pending_2fa

    # ── Export with filters ──────────────────────────────────────────────────
    def _filtered(self, phone_only=False, unsaved_only=False):
        out = self._results
        if phone_only:  out = [r for r in out if r["phone"]]
        if unsaved_only: out = [r for r in out if not r["is_mutual"]]
        return out

    def export_csv(self, phone_only=False, unsaved_only=False):
        rows = self._filtered(phone_only, unsaved_only)
        if not rows: return {"error": "No contacts match the selected filters."}
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        out_path = Path.home() / "Desktop" / f"tg_contacts_{date_str}.csv"
        fields   = ["first_name", "last_name", "username", "phone",
                    "last_seen", "is_mutual", "is_premium", "source_group"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        return {"path": str(out_path), "count": len(rows)}

    def export_json(self, phone_only=False, unsaved_only=False):
        rows = self._filtered(phone_only, unsaved_only)
        if not rows: return {"error": "No contacts match the selected filters."}
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        out_path = Path.home() / "Desktop" / f"tg_contacts_{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        return {"path": str(out_path), "count": len(rows)}

    def get_results(self):
        return self._results

    def _emit(self, event, data):
        if self._window:
            payload = json.dumps({"event": event, "data": data}, default=str)
            self._window.evaluate_js(f"window.onTelegramEvent({payload})")


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api = TelegramAPI()
    html_path = Path(__file__).parent / "ui.html"
    window = webview.create_window(
        "tg_harvest", str(html_path),
        js_api=api,
        width=900, height=660,
        resizable=False,
        background_color="#0d0d0d",
        text_select=False,
    )
    api.set_window(window)
    webview.start(debug=False)
