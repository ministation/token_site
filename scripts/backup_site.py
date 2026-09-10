#!/usr/bin/env python3
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def backup(src, dst_dir, keep):
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = dst_dir / f"social_{stamp}.db"
    src_conn = sqlite3.connect(src)
    try:
        dst_conn = sqlite3.connect(out)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    for old in sorted(dst_dir.glob("social_*.db"))[:-keep]:
        old.unlink()
    print(out)
    return out


def main():
    parser = argparse.ArgumentParser(description="Snapshot SQLite DB with rotation")
    parser.add_argument("--src", default=os.getenv("SOCIAL_DB_PATH", "social.db"))
    parser.add_argument("--dir", default=os.getenv("BACKUP_DIR", "backups"))
    parser.add_argument("--keep", type=int, default=int(os.getenv("BACKUP_KEEP", "14")))
    args = parser.parse_args()
    if not os.path.exists(args.src):
        sys.exit(f"source db not found: {args.src}")
    conn = sqlite3.connect(args.src)
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()
    if ok != "ok":
        sys.exit(f"integrity check failed: {ok}")
    backup(args.src, args.dir, args.keep)


if __name__ == "__main__":
    main()