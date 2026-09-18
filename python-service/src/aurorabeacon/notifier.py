"""
notifier.py

Sends push notifications via ntfy.sh. One function, no dependencies beyond
httpx. Deliberately doesn't know anything about scoring/thresholds - it
just sends whatever title/message it's given.
"""

import httpx

# Keep this private - anyone who knows it can read or post to your topic.
NTFY_TOPIC = "aurorabeacon-invss-x7f2q"  # replace with your own


def send_notification(title: str, message: str, priority: str = "default") -> None:
    httpx.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority},
    )


if __name__ == "__main__":
    send_notification("AuroraBeacon test", "If you see this, second ntfy is working!")