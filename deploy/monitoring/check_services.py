#!/usr/bin/env python3
import argparse
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = os.getenv("MAX_API_BASE", "https://api.icq.net/bot/v1")
API_TOKEN = os.getenv("MAX_API_TOKEN", "")
DEFAULT_CHAT = os.getenv("MAX_CHAT_ID", "")


def parse_targets(text):
    targets = []
    for item in text.replace("\n", ",").split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            host, port = item.rsplit(":", 1)
            targets.append((host, int(port)))
        else:
            targets.append((item, None))
    return targets


def tcp_ok(host, port, timeout):
    if port is None:
        return True
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def send_text(token, chat_id, text):
    data = urllib.parse.urlencode({"token": token, "chatId": chat_id, "text": text}).encode()
    req = urllib.request.Request(f"{API_BASE}/messages/sendText", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"{exc.code}: {exc.read().decode()}\n")


def main():
    parser = argparse.ArgumentParser(description="Check reachability of services and alert to MAX")
    parser.add_argument("targets", nargs="*", help="host:port list")
    parser.add_argument("--file", default=os.getenv("CHECK_TARGETS_FILE", "/etc/ministation/check_targets.txt"))
    parser.add_argument("--state", default="/var/lib/ministation/check_services.state")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--token", default=API_TOKEN or None)
    parser.add_argument("--chat", default=DEFAULT_CHAT or None)
    args = parser.parse_args()

    targets = []
    if args.targets:
        targets = parse_targets(",".join(args.targets))
    elif args.file and os.path.exists(args.file):
        with open(args.file) as fh:
            targets = parse_targets(fh.read())
    else:
        targets = parse_targets(os.getenv("CHECK_TARGETS", ""))

    if not targets:
        parser.error("no targets: pass args, --file, or CHECK_TARGETS")

    down = [f"{host}:{port}" if port else host for host, port in targets if not tcp_ok(host, port, args.timeout)]

    state = Path(args.state)
    was_down = state.exists() and state.read_text().strip() == "down"

    if down:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("down")
        if not was_down and args.token and args.chat:
            send_text(args.token, args.chat, "ALERT: DOWN: " + ", ".join(down))
        print("DOWN: " + ", ".join(down))
        sys.exit(1)

    if was_down and args.token and args.chat:
        send_text(args.token, args.chat, "OK: all services up")
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("ok")
    print("ok")
    sys.exit(0)


if __name__ == "__main__":
    main()