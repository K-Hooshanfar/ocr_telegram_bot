#!/usr/bin/env python3
"""Obtain a JWT token for the Telegram bot or API clients."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description="Get a JWT token from the OCR API.")
    parser.add_argument("--url", default="http://localhost:8067", help="API base URL")
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--password", default="changeme", help="Login password")
    args = parser.parse_args()

    data = urllib.parse.urlencode(
        {"username": args.username, "password": args.password}
    ).encode()
    req = urllib.request.Request(
        f"{args.url}/user/login",
        data=data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        sys.exit(1)

    token = body["access_token"]
    print(token)
    print("\nAdd this to your .env file as OCR_API_KEY=", file=sys.stderr)


if __name__ == "__main__":
    main()
