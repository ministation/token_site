#!/usr/bin/env python3
import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.getenv("MAX_API_BASE", "https://api.icq.net/bot/v1")
API_TOKEN = os.getenv("MAX_API_TOKEN", "")
DEFAULT_CHAT = os.getenv("MAX_CHAT_ID", "")


def send_text(token, chat_id, text):
    data = urllib.parse.urlencode({"token": token, "chatId": chat_id, "text": text}).encode()
    req = urllib.request.Request(f"{API_BASE}/messages/sendText", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"{exc.code}: {exc.read().decode()}\n")
        return 1
    if '"ok": false' in body:
        sys.stderr.write(body + "\n")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Send a message to MAX via bot API")
    parser.add_argument("text", help="message text")
    parser.add_argument("--token", default=API_TOKEN or None, help="bot token or set MAX_API_TOKEN")
    parser.add_argument("--chat", default=DEFAULT_CHAT or None, help="chatId or set MAX_CHAT_ID")
    args = parser.parse_args()
    if not args.token or not args.chat:
        parser.error("set MAX_API_TOKEN and MAX_CHAT_ID env vars or pass --token/--chat")
    sys.exit(send_text(args.token, args.chat, args.text))


if __name__ == "__main__":
    main()