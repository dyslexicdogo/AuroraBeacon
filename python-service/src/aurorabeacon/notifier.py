"""
notifier.py

Sends push notifications via ntfy.sh. One function, no dependencies beyond
httpx. Deliberately doesn't know anything about scoring/thresholds - it
just sends whatever title/message it's given.
"""

import httpx
import os

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")


def send_notification(title: str, message: str, priority: str = "default") -> None:
    if not NTFY_TOPIC:
        print("[notifier] NTFY_TOPIC not set - skipping notification")
        return
    httpx.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority},
    )


if __name__ == "__main__":
    send_notification("AuroraBeacon test", "If you see this, second ntfy is working!")