import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

credentials_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])

credentials = Credentials.from_service_account_info(
    credentials_info,
    scopes=scopes
)

client = gspread.authorize(credentials)

spreadsheet = client.open_by_key(SPREADSHEET_ID)

# Read Standings
standings = spreadsheet.worksheet("Standings")
standings_rows = standings.get_all_values()

print(f"Found {len(standings_rows)} rows in Standings.")

print("\nFirst 5 games:")
for row in standings_rows[1:6]:
    print(row[10:18])


# Read Batting
batting = spreadsheet.worksheet("Batting")
batting_rows = batting.get_all_values()

print(f"\nFound {len(batting_rows)} rows in Batting.")

print("\nBatting headers:")
print(batting_rows[0])

print("\nFirst 10 batting rows:")
for row in batting_rows[1:11]:
    print(row)

# Read Pitching
pitching = spreadsheet.worksheet("Pitching")
pitching_rows = pitching.get_all_values()

print(f"\nFound {len(pitching_rows)} rows in Pitching.")

print("\nPitching headers:")
print(pitching_rows[0])

print("\nFirst 10 pitching rows:")
for row in pitching_rows[1:11]:
    print(row)
