"""Preflight the live suite: prime macOS automation permissions and health-check the
verifiers, so an overnight run isn't silently sabotaged by a permission dialog.

The verifiers query Notes/Reminders/etc. via AppleScript. The FIRST such call triggers a
macOS "allow this app to control Notes?" dialog; unapproved, it returns -1743 and every
Notes task reports a false failure. Run this ONCE, approve each dialog (or grant in
System Settings > Privacy & Security > Automation), and re-run until every line says OK.

Run:  python -m bench.suite.preflight
"""

from __future__ import annotations

import subprocess

# app -> a harmless query that forces its automation-permission dialog to appear.
PROBES = {
    "Notes": 'tell application "Notes" to count notes',
    "Reminders": 'tell application "Reminders" to count lists',
    "Calendar": 'tell application "Calendar" to count calendars',
    "Contacts": 'tell application "Contacts" to count people',
    "System Events": 'tell application "System Events" to count processes',
}


def probe(app: str, script: str) -> str:
    try:
        subprocess.run(["open", "-a", app], capture_output=True, timeout=10)  # ensure it's running
    except (subprocess.TimeoutExpired, OSError):
        pass
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20)
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"ERROR ({e})"
    if r.returncode == 0:
        return f"OK ({r.stdout.strip()})"
    err = r.stderr or ""
    if "-1743" in err or "Not authorized" in err:
        return "DENIED — approve the dialog, or System Settings > Privacy & Security > Automation"
    return f"ERROR ({err.strip()[:80]})"


def prep_environment() -> None:
    """Environment tweaks that remove avoidable task friction. Currently: make TextEdit
    default to PLAIN TEXT, so 'save as X.txt' doesn't fight Rich Text -> .rtf (the root
    cause of the text_06 timeout and text_10 content miss). Revert with:
        defaults write com.apple.TextEdit RichText -bool true
    """
    try:
        subprocess.run(["defaults", "write", "com.apple.TextEdit", "RichText", "-bool", "false"],
                       capture_output=True, timeout=10)
        print("  TextEdit      : set to plain-text default (avoids .rtf save friction)")
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  TextEdit      : could not set plain-text default ({e})")


def main() -> None:
    print("=== preflight: environment prep ===")
    prep_environment()
    print("=== preflight: macOS automation permissions (verifiers need these) ===")
    results = {app: probe(app, script) for app, script in PROBES.items()}
    for app, res in results.items():
        print(f"  {app:14}: {res}")
    denied = [a for a, r in results.items() if not r.startswith("OK")]
    if denied:
        print(f"\n{len(denied)} not ready: {', '.join(denied)}")
        print("Approve the macOS dialog(s) shown, or grant in System Settings > Privacy & "
              "Security > Automation, then re-run this until every line says OK.")
        raise SystemExit(1)
    print("\nAll permissions granted — verifiers can see Notes/Reminders/etc. Ready to run the suite.")


if __name__ == "__main__":
    main()
