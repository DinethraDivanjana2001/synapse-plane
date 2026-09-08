"""One-time INTERACTIVE Google Calendar OAuth setup.

Run this yourself, locally, in a terminal with a real browser available:

    python scripts/setup_google_calendar_auth.py

It opens a browser for you to sign in and grant calendar access, then saves
the resulting token to GOOGLE_CALENDAR_TOKEN_PATH (default: token.json).
After that, the app can read/refresh the token on its own — this script
never needs to run again unless you revoke access or delete the token file.

This cannot be run by an AI agent or in a headless environment: Google's
consent screen requires an actual human click in an actual browser.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from synapse_plane.config import get_settings  # noqa: E402
from synapse_plane.tools.google_calendar_tool import SCOPES  # noqa: E402


def main() -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    settings = get_settings()
    credentials_path = Path(settings.google_calendar_credentials_path)
    token_path = Path(settings.google_calendar_token_path)

    if not credentials_path.exists():
        print(f"Missing {credentials_path}. Download an OAuth 'installed app' client")
        print("from Google Cloud Console (Calendar API enabled) and save it there.")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())
    print(f"Saved token to {token_path}. Set CALENDAR_PROVIDER=google in .env to use it.")


if __name__ == "__main__":
    main()
