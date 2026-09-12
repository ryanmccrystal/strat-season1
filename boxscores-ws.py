import os
import json
import re
import gspread
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"


TEAM_NAMES = {
    "PDX": "Portland",
    "IOWA": "Iowa",
    "PAW": "Pawtucket",
    "RICH": "Richmond",
    "OMA": "Omaha",
    "DUNE": "Dunedin",
}


TEAM_NICKNAMES = {
    "Portland Beavers": "Beavers",
    "Iowa Cubs": "Cubs",
    "Pawtucket Red Sox": "Red Sox",
    "Richmond Braves": "Braves",
    "Omaha Royals": "Royals",
    "Dunedin Blue Jays": "Blue Jays",
}


def get_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT"]
    )

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    return client.open_by_key(
        SPREADSHEET_ID
    )


def game_number(game_id):

    match = re.search(
        r"\d+",
        game_id
    )

    if match:
        return int(match.group())

    return 999999


# ============================================================
# WORLD SERIES GAMES
# ============================================================

def get_games(standings):

    rows = standings.get_all_values()

    games = []

    for row in rows[1:]:

        if len(row) < 17:
            continue

        game_id = row[10].strip()

        # WORLD SERIES GAMES ONLY
        if not game_id.startswith("WS"):
            continue

        games.append({
            "game_id": game_id,
            "date": row[11].strip(),
            "winner": row[12].strip(),
            "winner_runs": row[13].strip(),
            "loser": row[14].strip(),
            "loser_runs": row[15].strip(),
            "note": row[16].strip(),
        })

    games.sort(
        key=lambda x: game_number(
            x["game_id"]
        )
    )

    return games


def get_player_positions(batting_stats):

    rows = batting_stats.get_all_values()

    positions = {}

    for row in rows[1:]:

        if len(row) < 3:
            continue

        player_name = row[1].strip()
        position = row[2].strip()

        if player_name:
            positions[player_name] = position

    return positions


# ============================================================
# WORLD SERIES BATTING
# ============================================================

def get_batting_data(
    batting,
    player_positions
):

    rows = batting.get_all_values()

    batting_by_game = {}

    for row in rows[1:]:

        if len(row) < 28:
            continue

        team_code = row[0].strip()
        opponent_code = row[1].strip()
        batter = row[2].strip()
        pa = row[4].strip()
        game_id = row[27].strip()

        if not game_id:
            continue

        # WORLD SERIES GAMES ONLY
        if not game_id.startswith("WS"):
            continue

        if pa == "0":
            continue

        position = player_positions.get(
            batter,
            ""
        )

        player = {
            "team_code": team_code,

            "team": TEAM_NAMES.get(
                team_code,
                team_code
            ),

            "opponent_code": opponent_code,

            "opponent": TEAM_NAMES.get(
                opponent_code,
                opponent_code
            ),

            "batter": batter,
            "position": position,

            "AB": row[5].strip(),
            "R": row[6].strip(),
            "H": row[7].strip(),
            "RBI": row[8].strip(),
            "BB": row[9].strip(),
            "K": row[10].strip(),

            "2B": row[11].strip(),
            "3B": row[12].strip(),
            "HR": row[13].strip(),
            "SB": row[14].strip(),
            "CS": row[15].strip(),
            "GIDP": row[16].strip(),
            "SF": row[17].strip(),
            "E": row[20].strip(),
            "SH": row[29].strip(),
        }

        if game_id not in batting_by_game:

            batting_by_game[game_id] = []

        batting_by_game[game_id].append(
            player
        )

    return batting_by_game


# ============================================================
# WORLD SERIES PITCHING
# ============================================================

def get_pitching_data(pitching):

    rows = pitching.get_all_values()

    pitching_by_game = {}

    for row in rows[1:]:

        if len(row) < 16:
            continue

        pitcher = row[0].strip()
        team_code = row[1].strip()
        opponent_code = row[2].strip()

        game_id = (
            row[30].strip()
            if len(row) > 30
            else ""
        )

        if not pitcher or not game_id:
            continue

        # WORLD SERIES GAMES ONLY
        if not game_id.startswith("WS"):
            continue

        pitcher_data = {

            "pitcher": pitcher,

            "team_code": team_code,

            "team": TEAM_NAMES.get(
                team_code,
                team_code
            ),

            "opponent_code": opponent_code,

            "opponent": TEAM_NAMES.get(
                opponent_code,
                opponent_code
            ),

            "IP": row[4].strip(),
            "H": row[6].strip(),
            "R": row[7].strip(),
            "ER": row[8].strip(),
            "BB": row[9].strip(),
            "K": row[10].strip(),
            "W": row[11].strip(),
            "L": row[12].strip(),
            "HLD": row[13].strip(),
            "SV": row[14].strip(),
            "BS": row[15].strip(),
        }

        if game_id not in pitching_by_game:

            pitching_by_game[game_id] = []

        pitching_by_game[game_id].append(
            pitcher_data
        )

    return pitching_by_game


def make_totals(players):

    total_ab = 0
    total_r = 0
    total_h = 0
    total_rbi = 0
    total_bb = 0
    total_k = 0

    for player in players:

        total_ab += int(
            player["AB"] or 0
        )

        total_r += int(
            player["R"] or 0
        )

        total_h += int(
            player["H"] or 0
        )

        total_rbi += int(
            player["RBI"] or 0
        )

        total_bb += int(
            player["BB"] or 0
        )

        total_k += int(
            player["K"] or 0
        )

    return {
        "AB": total_ab,
        "R": total_r,
        "H": total_h,
        "RBI": total_rbi,
        "BB": total_bb,
        "K": total_k,
    }


def html_escape(value):

    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def make_team_section(
    team_code,
    players
):

    team_name = TEAM_NAMES.get(
        team_code,
        team_code
    )

    team_players = [
        player
        for player in players
        if player["team_code"] == team_code
    ]

    totals = make_totals(
        team_players
    )

    html = f"""
    <section class="team-section">

        <table class="batting-table">

            <thead>

                <tr>

                    <th class="player-column">
                        {html_escape(team_name)}
                    </th>

                    <th>AB</th>
                    <th>R</th>
                    <th>H</th>
                    <th>BI</th>
                    <th>BB</th>
                    <th>K</th>

                </tr>

            </thead>

            <tbody>
    """

    for player in team_players:

        batter_name = html_escape(
            player["batter"]
        )

        position = html_escape(
            player["position"]
        )

        if position:

            display_name = (
                f"{batter_name} {position}"
            )

        else:

            display_name = batter_name

        html += f"""
                <tr>

                    <td class="player-name">
                        {display_name}
                    </td>

                    <td>{html_escape(player["AB"])}</td>
                    <td>{html_escape(player["R"])}</td>
                    <td>{html_escape(player["H"])}</td>
                    <td>{html_escape(player["RBI"])}</td>
                    <td>{html_escape(player["BB"])}</td>
                    <td>{html_escape(player["K"])}</td>

                </tr>
        """

    html += f"""
                <tr class="totals">

                    <td class="player-name">
                        Totals
                    </td>

                    <td>{totals["AB"]}</td>
                    <td>{totals["R"]}</td>
                    <td>{totals["H"]}</td>
                    <td>{totals["RBI"]}</td>
                    <td>{totals["BB"]}</td>
                    <td>{totals["K"]}</td>

                </tr>

            </tbody>

        </table>

    </section>
    """

    return html


def get_pitcher_decision(
    pitcher
):

    if pitcher["W"]:
        return "W"

    if pitcher["L"]:
        return "L"

    if pitcher["HLD"]:
        return "H"

    if pitcher["SV"]:
        return "S"

    if pitcher["BS"]:
        return "BS"

    return ""


def update_pitcher_record(
    records,
    pitcher,
    decision
):

    if pitcher not in records:

        records[pitcher] = {
            "W": 0,
            "L": 0,
            "H": 0,
            "S": 0,
            "BS": 0,
        }

    if decision == "W":

        records[pitcher]["W"] += 1

    elif decision == "L":

        records[pitcher]["L"] += 1

    elif decision == "H":

        records[pitcher]["H"] += 1

    elif decision == "S":

        records[pitcher]["S"] += 1

    elif decision == "BS":

        records[pitcher]["BS"] += 1


def pitcher_display_name(
    pitcher,
    decision,
    records
):

    name = html_escape(
        pitcher["pitcher"]
    )

    if pitcher["pitcher"] not in records:

        records[pitcher["pitcher"]] = {
            "W": 0,
            "L": 0,
            "H": 0,
            "S": 0,
            "BS": 0,
        }

    if not decision:
        return name

    record = records[
        pitcher["pitcher"]
    ]

    if decision == "W":

        return (
            f"{name} W, "
            f"{record['W'] + 1}-"
            f"{record['L']}"
        )

    if decision == "L":

        return (
            f"{name} L, "
            f"{record['W']}-"
            f"{record['L'] + 1}"
        )

    if decision == "H":

        return (
            f"{name} H, "
            f"{record['H'] + 1}"
        )

    if decision == "S":

        return (
            f"{name} S, "
            f"{record['S'] + 1}"
        )

    if decision == "BS":

        return (
            f"{name} BS, "
            f"{record['BS'] + 1}"
        )

    return name


# ============================================================
# WORLD SERIES NOTE TOTALS
# ============================================================

def get_note_season_totals(
    games,
    batting_by_game
):

    season_totals = {}

    for game in games:

        game_id = game["game_id"]

        players = batting_by_game.get(
            game_id,
            []
        )

        for player in players:

            player_name = player["batter"]

            if player_name not in season_totals:

                season_totals[player_name] = {
                    "E": 0,
                    "2B": 0,
                    "3B": 0,
                    "HR": 0,
                    "SB": 0,
                    "CS": 0,
                }

            for category in [
                "E",
                "2B",
                "3B",
                "HR",
                "SB",
                "CS",
            ]:

                value = player[category]

                if value:

                    season_totals[
                        player_name
                    ][category] += int(value)

        game["note_season_totals"] = {

            player_name: totals.copy()

            for player_name, totals
            in season_totals.items()
        }

    return season_totals


def make_notes_section(
    batting_rows,
    note_season_totals,
    linescore_rows
):

    categories_with_totals = [
        ("E", "E"),
        ("2B", "2B"),
        ("3B", "3B"),
        ("HR", "HR"),
        ("SB", "SB"),
        ("CS", "CS"),
    ]

    categories_without_totals = [
        ("GIDP", "GIDP"),
        ("SH", "SH"),
        ("SF", "SF"),
    ]

    parts = []

    lob_text = ""

    ordered_linescore_rows = sorted(
        linescore_rows,
        key=lambda row: (
            0
            if row["home_away"] == "A"
            else 1
        )
    )

    if len(ordered_linescore_rows) == 2:

        away = ordered_linescore_rows[0]
        home = ordered_linescore_rows[1]

        away_name = TEAM_NAMES.get(
            away["team_code"],
            away["team_code"]
        )

        home_name = TEAM_NAMES.get(
            home["team_code"],
            home["team_code"]
        )

        if away["LOB"] or home["LOB"]:

            lob_text = (
                f"<strong>LOB:</strong> "
                f"{html_escape(away_name)} "
                f"{html_escape(away['LOB'])}, "
                f"{html_escape(home_name)} "
                f"{html_escape(home['LOB'])}."
            )

    for category, label in categories_with_totals:

        events = []

        for player in batting_rows:

            value = player[category]

            if not value:
                continue

            try:
                count = int(value)

            except ValueError:
                continue

            if count <= 0:
                continue

            player_name = html_escape(
                player["batter"]
            )

            totals = note_season_totals.get(
                player["batter"],
                {}
            )

            season_total = totals.get(
                category,
                count
            )

            events.append(
                f"{player_name} ({season_total})"
            )

        if events:

            parts.append(
                f"<strong>{label}:</strong> "
                + ", ".join(events)
                + "."
            )

        if label == "E" and lob_text:

            parts.append(
                lob_text
            )

    for category, label in categories_without_totals:

        events = []

        for player in batting_rows:

            value = player[category]

            if not value:
                continue

            try:
                count = int(value)

            except ValueError:
                continue

            if count <= 0:
                continue

            events.append(
                html_escape(
                    player["batter"]
                )
            )

        if events:

            parts.append(
                f"<strong>{label}:</strong> "
                + ", ".join(events)
                + "."
            )

    if not parts:
        return ""

    return f"""
    <div class="notes">
        {" ".join(parts)}
    </div>
    """


def format_innings_pitched(ip):

    ip = str(ip).strip()

    if not ip:
        return ""

    if "1/3" in ip:

        whole = ip.replace(
            "1/3",
            ""
        ).strip()

        if whole:

            return (
                f"{html_escape(whole)}¹⁄₃"
            )

        return "¹⁄₃"

    if "2/3" in ip:

        whole = ip.replace(
            "2/3",
            ""
        ).strip()

        if whole:

            return (
                f"{html_escape(whole)}²⁄₃"
            )

        return "²⁄₃"

    return html_escape(ip)


def make_pitching_section(
    team_code,
    pitchers,
    records
):

    team_name = TEAM_NAMES.get(
        team_code,
        team_code
    )

    team_pitchers = [
        pitcher
        for pitcher in pitchers
        if pitcher["team_code"] == team_code
    ]

    html = f"""
    <section class="pitching-section">

        <table class="pitching-table">

            <thead>

                <tr>

                    <th class="pitcher-column">
                        {html_escape(team_name)}
                    </th>

                    <th>IP</th>
                    <th>H</th>
                    <th>R</th>
                    <th>ER</th>
                    <th>BB</th>
                    <th>K</th>

                </tr>

            </thead>

            <tbody>
    """

    for pitcher in team_pitchers:

        decision = get_pitcher_decision(
            pitcher
        )

        display_name = pitcher_display_name(
            pitcher,
            decision,
            records
        )

        html += f"""
                <tr>

                    <td class="pitcher-name">
                        {display_name}
                    </td>

                    <td>
                        {format_innings_pitched(
                            pitcher["IP"]
                        )}
                    </td>

                    <td>{html_escape(pitcher["H"])}</td>
                    <td>{html_escape(pitcher["R"])}</td>
                    <td>{html_escape(pitcher["ER"])}</td>
                    <td>{html_escape(pitcher["BB"])}</td>
                    <td>{html_escape(pitcher["K"])}</td>

                </tr>
        """

    html += """
            </tbody>

        </table>

    </section>
    """

    return html


def get_home_away_order(
    linescore
):

    rows = linescore.get_all_values()

    game_order = {}

    for row in rows[1:]:

        if len(row) < 5:
            continue

        game_id = row[1].strip()
        team_code = row[3].strip()
        home_away = row[4].strip().upper()

        if not game_id or not team_code:
            continue

        if not game_id.startswith("WS"):
            continue

        if game_id not in game_order:

            game_order[game_id] = {
                "away": None,
                "home": None,
            }

        if home_away == "A":

            game_order[game_id]["away"] = (
                team_code
            )

        elif home_away == "H":

            game_order[game_id]["home"] = (
                team_code
            )

    return game_order


def get_linescore_data(
    linescore
):

    rows = linescore.get_all_values()

    linescores_by_game = {}

    for row in rows[1:]:

        if len(row) < 22:
            continue

        game_id = row[1].strip()
        team_code = row[3].strip()
        home_away = row[4].strip().upper()

        if not game_id or not team_code:
            continue

        if not game_id.startswith("WS"):
            continue

        innings = []

        for index in range(5, 19):

            value = row[index].strip()

            innings.append(value)

        linescore = {
            "team_code": team_code,
            "home_away": home_away,
            "innings": innings,
            "R": row[19].strip(),
            "H": row[20].strip(),
            "E": row[21].strip(),
            "LOB": row[22].strip()
            if len(row) > 22
            else "",
            "note": row[23].strip()
            if len(row) > 23
            else "",
        }

        if game_id not in linescores_by_game:

            linescores_by_game[game_id] = []

        linescores_by_game[game_id].append(
            linescore
        )

    return linescores_by_game


def make_linescore_section(
    game,
    linescore_rows
):

    if not linescore_rows:
        return ""

    max_inning = 9

    note = game["note"].strip().upper()

    if note.startswith("F/"):

        try:

            max_inning = int(
                note.replace(
                    "F/",
                    ""
                )
            )

        except ValueError:

            max_inning = 9

    max_inning = min(
        max_inning,
        14
    )

    html = """
    <div class="linescore">

        <table class="linescore-table">

            <tbody>
    """

    ordered_rows = sorted(
        linescore_rows,
        key=lambda row: (
            0
            if row["home_away"] == "A"
            else 1
        )
    )

    for row in ordered_rows:

        team_name = TEAM_NAMES.get(
            row["team_code"],
            row["team_code"]
        )

        html += f"""
                <tr>

                    <td class="linescore-team">
                        {html_escape(team_name)}
                    </td>
        """

        for index in range(max_inning):

            value = row["innings"][index]

            if value == "":
                value = "0"

            inning_number = index + 1

            if (
                inning_number % 3 == 1
                and inning_number > 1
            ):

                html += (
                    '<td class="inning-group-start">'
                )

            else:

                html += "<td>"

            html += (
                f"{html_escape(value)}</td>"
            )

        html += """
                    <td class="linescore-separator">
                        —
                    </td>
        """

        html += f"""
                    <td class="linescore-total">
                        {html_escape(row["R"])}
                    </td>

                    <td class="linescore-total">
                        {html_escape(row["H"])}
                    </td>

                    <td class="linescore-total">
                        {html_escape(row["E"])}
                    </td>

                </tr>
        """

    html += """
            </tbody>

        </table>

    </div>
    """

    return html


def make_game_section(
    game,
    batting_rows,
    pitching_rows,
    records,
    home_away_order,
    linescore_rows
):

    teams = []

    game_id = game["game_id"]

    away_team = home_away_order.get(
        game_id,
        {}
    ).get("away")

    home_team = home_away_order.get(
        game_id,
        {}
    ).get("home")

    if away_team:
        teams.append(away_team)

    if home_team:
        teams.append(home_team)

    for player in batting_rows:

        if player["team_code"] not in teams:

            teams.append(
                player["team_code"]
            )

    for pitcher in pitching_rows:

        if pitcher["team_code"] not in teams:

            teams.append(
                pitcher["team_code"]
            )

    winner = TEAM_NICKNAMES.get(
        game["winner"],
        game["winner"]
    )

    loser = TEAM_NICKNAMES.get(
        game["loser"],
        game["loser"]
    )

    winner_runs = html_escape(
        game["winner_runs"]
    )

    loser_runs = html_escape(
        game["loser_runs"]
    )

    score_text = (
        f"{html_escape(winner)} "
        f"{winner_runs}, "
        f"{html_escape(loser)} "
        f"{loser_runs}"
    )

    if game["note"]:

        score_text += (
            f" <span class=\"extra-innings\">"
            f"{html_escape(game['note'])}"
            f"</span>"
        )

    html = f"""
    <article class="game">

        <div class="game-header">

            <div class="score">
                <strong>{score_text}</strong>
            </div>

            <div class="game-info">
                {html_escape(game["game_id"])}
                &nbsp; | &nbsp;
                {html_escape(game["date"])}
            </div>

        </div>
    """

    for team_code in teams:

        html += make_team_section(
            team_code,
            batting_rows
        )

    html += make_linescore_section(
        game,
        linescore_rows
    )

    note_season_totals = game.get(
        "note_season_totals",
        {}
    )

    notes_html = make_notes_section(
        batting_rows,
        note_season_totals,
        linescore_rows
    )

    html += notes_html

    for team_code in teams:

        html += make_pitching_section(
            team_code,
            pitching_rows,
            records
        )

    linescore_notes = []

    for row in linescore_rows:

        if row["note"].strip():

            linescore_notes.append(
                row["note"].strip()
            )

    if linescore_notes:

        html += (
            '<div class="linescore-note">'
        )

        for note in linescore_notes:

            html += (
                f"<em>{html_escape(note)}</em><br>"
            )

        html += "</div>"

    html += """
    </article>
    """

    return html


# ============================================================
# HTML
# ============================================================

def create_html(
    games,
    batting_by_game,
    pitching_by_game,
    home_away_order,
    linescore_by_game
):

    html = """<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Strat-o-Matic World Series Box Scores</title>

<link rel="preconnect"
      href="https://fonts.googleapis.com">

<link rel="preconnect"
      href="https://fonts.gstatic.com"
      crossorigin>

<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap"
      rel="stylesheet">

<style>

body {
    font-family: "Source Sans 3",
        Arial,
        Helvetica,
        sans-serif;

    background: #ffffff;
    color: #111111;

    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1800px;
    margin: 0 auto;
}

h1 {
    font-size: 26px;
    font-weight: 700;
    margin: 0 0 22px 0;
}

.games-grid {
    display: grid;

    grid-template-columns:
        repeat(5, minmax(0, 1fr));

    gap: 18px;
    align-items: start;
}

.game {
    margin: 0;
    padding: 0;
    border: none;
    font-size: 12px;
    min-width: 0;
}

.game-header {
    margin-bottom: 4px;
}

.score {
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 1px;
    line-height: 1.2;
}

.extra-innings {
    font-weight: 600;
    margin-left: 3px;
}

.game-info {
    font-size: 11px;
    color: #666;
    line-height: 1.2;
}

.team-section {
    margin-top: 4px;
}

.batting-table,
.pitching-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 14px;
}

.batting-table th.player-column,
.batting-table td.player-name,
.pitching-table th.pitcher-column,
.pitching-table td.pitcher-name {
    width: 46%;
    text-align: left;
}

.batting-table th:not(.player-column),
.batting-table td:not(.player-name),
.pitching-table th:not(.pitcher-column),
.pitching-table td:not(.pitcher-name) {
    width: 9%;
    text-align: center;
}

.batting-table th,
.pitching-table th {
    font-weight: 600;
    border-bottom: 1px solid #222;
    border-top: 1px solid #222;
    padding: 2px 2px;
    line-height: 1.05;
}

.batting-table td,
.pitching-table td {
    padding: 2px 2px;
    line-height: 1.05;
}

.batting-table td.player-name,
.pitching-table td.pitcher-name {
    white-space: nowrap;
}

.batting-table tr.totals {
    border-top: 1px solid #222;
    font-weight: 700;
}

.pitching-section {
    margin-top: 4px;
}

.linescore {
    margin-top: 4px;
    margin-bottom: 4px;
}

.linescore-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 14px;
    border-top: 1px solid #222;
    border-bottom: 1px solid #222;
}

.linescore-table td {
    padding: 2px 0px;
    text-align: center;
    line-height: 1.05;
}

.linescore-table .linescore-team {
    width: 30%;
    text-align: left;
    font-weight: 700;
    padding-right: 4px;
}

.linescore-table .inning-group-start {
    padding-left: 10px;
}

.linescore-table .linescore-total {
    font-weight: 600;
    padding-left: 3px;
}

.linescore-table .linescore-separator {
    width: 5%;
    padding-left: 5px;
    padding-right: 5px;
}

.notes {
    margin-top: 4px;
    margin-bottom: 4px;
    font-size: 14px;
    line-height: 1.25;
}

.linescore-note {
    margin-top: 4px;
    font-size: 13px;
    line-height: 1.25;
}

.ws-game-wrapper {
    min-width: 0;
}

.ws-game-title {
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 4px;
}

@media (max-width: 1500px) {

    .games-grid {
        grid-template-columns:
            repeat(4, minmax(0, 1fr));
    }

}

@media (max-width: 1200px) {

    .games-grid {
        grid-template-columns:
            repeat(3, minmax(0, 1fr));
    }

}

@media (max-width: 900px) {

    body {
        padding: 15px;
    }

    .games-grid {
        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }

}

@media (max-width: 600px) {

    body {
        padding: 10px;
    }

    .games-grid {
        grid-template-columns: 1fr;
    }

    .game {
        padding: 14px;
    }

    .score {
        font-size: 19px;
    }

    .game-info {
        font-size: 12px;
    }

    .batting-table th.player-column,
    .pitching-table th.pitcher-column {
        text-align: left;
        font-weight: 700;
    }

    .batting-table,
    .pitching-table {
        font-size: 13px;
    }

    .batting-table th,
    .batting-table td,
    .pitching-table th,
    .pitching-table td {
        padding: 4px;
    }

    .notes {
        font-size: 12px;
    }

}

</style>

</head>

<body>

<div class="container">

<h1>Strat-o-Matic World Series Box Scores</h1>

<div class="games-grid">
"""

    get_note_season_totals(
        games,
        batting_by_game
    )

    records = {}

    for game in games:
    
        game_id = game["game_id"]
    
        batting_rows = batting_by_game.get(
            game_id,
            []
        )
    
        pitching_rows = pitching_by_game.get(
            game_id,
            []
        )
    
        linescore_rows = linescore_by_game.get(
            game_id,
            []
        )
    
        # World Series game label
        ws_number = game_id.replace(
            "WS",
            ""
        )

        html += """
        <div class="ws-game-wrapper">
        """

        html += f"""
        <div class="ws-game-title">
            Game {html_escape(ws_number)}
        </div>
        """

        html += make_game_section(
            game,
            batting_rows,
            pitching_rows,
            records,
            home_away_order,
            linescore_rows
        )

        html += """
        </div>
        """

        for pitcher in pitching_rows:

            decision = get_pitcher_decision(
                pitcher
            )

            if decision:

                update_pitcher_record(
                    records,
                    pitcher["pitcher"],
                    decision
                )

    html += """
</div>

</div>

</body>

</html>
"""

    return html


# ============================================================
# MAIN
# ============================================================

def main():

    spreadsheet = get_google_sheet()

    standings = spreadsheet.worksheet(
        "Standings"
    )

    batting = spreadsheet.worksheet(
        "BatWS"
    )

    pitching = spreadsheet.worksheet(
        "PitWS"
    )

    batting_stats = spreadsheet.worksheet(
        "Batting Stats"
    )

    linescore = spreadsheet.worksheet(
        "Linescore"
    )

    games = get_games(
        standings
    )

    print(
        f"Found {len(games)} World Series games."
    )

    player_positions = get_player_positions(
        batting_stats
    )

    batting_by_game = get_batting_data(
        batting,
        player_positions
    )

    pitching_by_game = get_pitching_data(
        pitching
    )

    home_away_order = get_home_away_order(
        linescore
    )

    linescore_by_game = get_linescore_data(
        linescore
    )

    html = create_html(
        games,
        batting_by_game,
        pitching_by_game,
        home_away_order,
        linescore_by_game
    )

    with open(
        "boxscores-ws.html",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html)

    print(
        f"Created boxscores-ws.html "
        f"with {len(games)} World Series games."
    )


if __name__ == "__main__":
    main()
