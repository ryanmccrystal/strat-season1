import os
import json
import html
import re
import urllib.request

import gspread
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"

TEAM_TABS = [
    "Iowa",
    "Omaha",
    "Richmond",
    "Pawtucket",
    "Dunedin",
    "Portland"
    # Add the rest of your team tab names here
]

LOGO_DIRECTORY = "logos"


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


def html_escape(value):

    return html.escape(
        str(value),
        quote=True
    )


def get_team_data(
    spreadsheet,
    team_tab
):

    worksheet = spreadsheet.worksheet(
        team_tab
    )

    return worksheet.get_all_values()


def get_logo_map(spreadsheet):

    worksheet = spreadsheet.worksheet(
        "Logos"
    )

    rows = worksheet.get(
        "A1:B1500",
        value_render_option="FORMULA"
    )

    logo_map = {}

    for row in rows:

        if len(row) < 2:
            continue

        real_team = str(
            row[0]
        ).strip()

        image_formula = str(
            row[1]
        ).strip()

        if not real_team:
            continue

        if not image_formula.lower().startswith(
            "=image("
        ):
            continue

        start = image_formula.find('"')
        end = image_formula.rfind('"')

        if start == -1 or end <= start:
            continue

        logo_url = image_formula[
            start + 1:end
        ]

        if logo_url:

            logo_map[real_team] = logo_url

    return logo_map


def make_logo_filename(real_team):

    filename = real_team.lower()

    filename = re.sub(
        r"[^a-z0-9]+",
        "-",
        filename
    )

    filename = filename.strip("-")

    return filename + ".gif"


def download_required_logos(
    logo_map,
    rows
):

    os.makedirs(
        LOGO_DIRECTORY,
        exist_ok=True
    )

    # Find all Real Tm values that actually
    # appear in the Iowa spreadsheet.
    required_teams = set()

    for row in rows:

        if len(row) <= 2:
            continue

        real_team = row[2].strip()

        if real_team:
            required_teams.add(
                real_team
            )

    downloaded = 0
    already_exists = 0
    missing = 0

    for real_team in sorted(
        required_teams
    ):

        logo_url = logo_map.get(
            real_team
        )

        if not logo_url:

            missing += 1
        
            print(
                f"NO LOGO FOUND: [{real_team}]"
            )
        
            continue

        filename = make_logo_filename(
            real_team
        )

        local_path = os.path.join(
            LOGO_DIRECTORY,
            filename
        )

        if os.path.exists(
            local_path
        ):

            already_exists += 1

            continue

        try:

            print(
                f"Downloading logo: {real_team}"
            )

            request = urllib.request.Request(
                logo_url,
                headers={
                    "User-Agent":
                        "Mozilla/5.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=15
            ) as response:

                image_data = response.read()

            with open(
                local_path,
                "wb"
            ) as file:

                file.write(
                    image_data
                )

            downloaded += 1

        except Exception as error:

            print(
                f"Could not download logo "
                f"for {real_team}: {error}"
            )

    print(
        "Logo summary: "
        f"{downloaded} downloaded, "
        f"{already_exists} already existed, "
        f"{missing} missing."
    )


def find_section_rows(rows):

    sections = {}

    for index, row in enumerate(rows):

        values = [
            cell.strip()
            for cell in row
        ]

        if "Pitching" in values:

            sections["Pitching"] = index

        elif "Batting" in values:

            sections["Batting"] = index

        elif "Catching" in values:

            sections["Catching"] = index

        elif "Fielding" in values:

            sections["Fielding"] = index

    return sections


def get_section_rows(
    rows,
    section_start,
    next_section_start=None
):

    start = section_start + 1

    if next_section_start is not None:

        end = next_section_start

    else:

        end = len(rows)

    section = rows[start:end]

    while section and not any(
        cell.strip()
        for cell in section[0]
    ):

        section.pop(0)

    while section and not any(
        cell.strip()
        for cell in section[-1]
    ):

        section.pop()

    return section


def make_table(
    section_rows,
    section_name
):

    if len(section_rows) < 2:

        return ""

    header = section_rows[0]

    data_rows = section_rows[1:]

    # Find the final used column.
    last_column = 0

    for row in section_rows:

        for index, value in enumerate(row):

            if value.strip():

                last_column = max(
                    last_column,
                    index
                )

    header = header[
        :last_column + 1
    ]

    # Find the Real Tm / Tm-Yr column.
    real_team_column = None

    for index, value in enumerate(header):

        header_value = (
            value.strip().lower()
        )

        if header_value in (
            "real tm",
            "tm/yr",
            "tm - yr"
        ):

            real_team_column = index

            break

    html_output = """
    <div class="table-wrapper">

        <table class="team-stats-table">

            <thead>

                <tr>

                    <th class="logo-header"></th>
    """

    # Skip spreadsheet Column A because
    # that column is reserved for the logo.
    for value in header[1:]:

        html_output += (
            f"<th>{html_escape(value)}</th>"
        )

    html_output += """
                </tr>

            </thead>

            <tbody>
    """

    for row_index, row in enumerate(
        data_rows
    ):

        row = row[
            :last_column + 1
        ]

        # -----------------------------------------
        # Divider after the fourth starting pitcher.
        # -----------------------------------------
        
        if (
            section_name == "Pitching"
            and row_index == 4
        ):
        
            html_output += """
                <tr class="section-divider">
                    <td colspan="100%"></td>
                </tr>
            """
        
        
        # -----------------------------------------
        # Divider before Pitching Team row.
        # -----------------------------------------
        
        if (
            section_name == "Pitching"
            and row_index == 10
        ):
        
            html_output += """
                <tr class="section-divider">
                    <td colspan="100%"></td>
                </tr>
            """
        
        
        # -----------------------------------------
        # Divider before Batting Team Totals.
        # There are always nine individual batters.
        # -----------------------------------------
        
        if (
            section_name == "Batting"
            and row_index == 9
        ):
        
            html_output += """
                <tr class="section-divider">
                    <td colspan="100%"></td>
                </tr>
            """
        
        
        html_output += "<tr>"

        # -----------------------------------------
        # Determine the local logo.
        # -----------------------------------------

        logo_filename = ""

        if (
            real_team_column is not None
            and len(row) > real_team_column
        ):

            real_team = row[
                real_team_column
            ].strip()

            if real_team:

                possible_filename = (
                    make_logo_filename(
                        real_team
                    )
                )

                possible_path = os.path.join(
                    LOGO_DIRECTORY,
                    possible_filename
                )

                if os.path.exists(
                    possible_path
                ):

                    logo_filename = (
                        possible_filename
                    )

        # -----------------------------------------
        # Logo cell.
        # -----------------------------------------

        if logo_filename:

            html_output += f"""
                <td class="logo-cell">

                    <img
                        src="../logos/{html_escape(logo_filename)}"
                        class="player-logo"
                        alt=""
                    >

                </td>
            """

        else:

            html_output += (
                '<td class="logo-cell"></td>'
            )

        # -----------------------------------------
        # Spreadsheet data.
        # -----------------------------------------

        for value in row[1:]:

            display_value = html_escape(value)
        
            display_value = display_value.replace(
                " 1/3",
                '<span class="fraction">¹⁄₃</span>'
            )
        
            display_value = display_value.replace(
                " 2/3",
                '<span class="fraction">²⁄₃</span>'
            )
        
            html_output += (
                f"<td>{display_value}</td>"
            )

        # Fill missing cells.
        expected_cells = (
            len(header) + 1
        )

        actual_cells = (
            len(row) + 1
        )

        missing = (
            expected_cells
            - actual_cells
        )

        for _ in range(missing):

            html_output += "<td></td>"

        html_output += "</tr>"

    html_output += """
            </tbody>

        </table>

    </div>
    """

    return html_output


def make_team_page(
    rows,
    team_tab
):

    sections = find_section_rows(
        rows
    )

    html_output = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>TEAM_TITLE_PLACEHOLDER - Strat-o-Matic</title>

<link rel="preconnect"
      href="https://fonts.googleapis.com">

<link rel="preconnect"
      href="https://fonts.gstatic.com"
      crossorigin>

<link
    href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap"
    rel="stylesheet"
>

<style>

    body {

        font-family:
            "Source Sans 3",
            Arial,
            Helvetica,
            sans-serif;

        background: #ffffff;

        color: #111111;

        margin: 0;

        padding: 25px;
    }


    .container {

        width: 100%;

        margin: 0 auto;
    }


    /* =========================
       TEAM HEADER
       ========================= */

    .team-header {

        margin-bottom: 25px;
    }


    .team-name {

        font-size: 32px;

        font-weight: 700;

        margin: 0 0 3px 0;
    }


    .team-record {

        font-size: 18px;

        margin-bottom: 2px;
    }


    .team-manager {

        font-size: 16px;

        color: #555555;
    }


    /* =========================
       SECTIONS
       ========================= */

    .stats-section {

        margin-bottom: 28px;
    }


    .stats-section h2 {

        font-size: 20px;

        font-weight: 700;

        margin: 0 0 6px 0;

        border-bottom: 1px solid #222;

        padding-bottom: 3px;
    }


    /* =========================
       CATCHING / FIELDING
       ========================= */

    .small-stats-row {

        display: grid;

        grid-template-columns: 1fr 1fr;

        gap: 30px;

        align-items: start;
    }


    .small-stats-row
    .stats-section {

        min-width: 0;
    }


    /* =========================
       TABLE
       ========================= */

    .table-wrapper {

        width: 100%;

        overflow-x: auto;
    }


    .team-stats-table {

        width: 100%;

        border-collapse: collapse;

        table-layout: auto;

        font-size: 14px;

        white-space: nowrap;
    }


    .team-stats-table th,
    .team-stats-table td {

        padding: 4px 7px;

        text-align: center;

        line-height: 1.15;
    }


    /* =========================
       LOGOS
       ========================= */

    .team-stats-table
    th.logo-header,
    .team-stats-table
    td.logo-cell {

        width: 28px;

        padding-left: 2px;

        padding-right: 2px;

        text-align: center;
    }


    .player-logo {

        width: 25px;

        height: 25px;

        object-fit: contain;

        vertical-align: middle;
    }


    /* =========================
       FRACTIONS
       ========================= */

    .fraction {

        font-size: 0.90em;

        vertical-align: 0.08em;
    }


    /* =========================
       FIRST TWO TEXT COLUMNS
       ========================= */

    .team-stats-table
    th:nth-child(2),
    .team-stats-table
    td:nth-child(2) {

        text-align: left;
    }


    .team-stats-table
    th:nth-child(3),
    .team-stats-table
    td:nth-child(3) {

        text-align: left;
    }


    .team-stats-table th {

        font-weight: 600;

        border-bottom: 1px solid #222;
    }


    /* =========================
       PITCHING / BATTING DIVIDERS
       ========================= */

    .team-stats-table
    tr.section-divider {

        height: 0;
    }


    .team-stats-table
    tr.section-divider td {

        padding: 0;

        height: 0;

        line-height: 0;

        border-bottom: 1px solid #222;
    }


    .team-stats-table
    tbody tr:last-child {

        border-bottom: 1px solid #222;
    }


    /* =========================
       HOVER
       ========================= */

    .team-stats-table
    tbody tr:hover {

        background: #f5f5f5;
    }


    /* =========================
       MOBILE
       ========================= */

    @media (max-width: 900px) {

        body {

            padding: 15px;
        }


        .team-name {

            font-size: 28px;
        }


        .team-stats-table {

            font-size: 13px;
        }


        .team-stats-table th,
        .team-stats-table td {

            padding: 3px 5px;
        }


        .player-logo {

            width: 25px;

            height: 25px;
        }


        .small-stats-row {

            grid-template-columns: 1fr;

            gap: 20px;
        }

    }

</style>

</head>

<body>

<div class="container">
"""

    # Replace the title placeholder with the current team name.
    html_output = html_output.replace(
        "TEAM_TITLE_PLACEHOLDER",
        html_escape(team_tab)
    )


    # -----------------------------------------
    # Team header
    # -----------------------------------------

    team_name = ""

    if rows and len(rows[0]) > 2:

        team_name = rows[0][2].strip()


    record = ""

    if len(rows) > 1 and len(rows[1]) > 2:

        record = rows[1][2].strip()


    manager = ""

    if len(rows) > 1 and len(rows[1]) > 3:

        manager = rows[1][3].strip()


    html_output += f"""
    <div class="team-header">

        <div class="team-name">

            {html_escape(team_name)}

        </div>

        <div class="team-record">

            {html_escape(record)}

        </div>

        <div class="team-manager">

            {html_escape(manager)}

        </div>

    </div>
"""


    # -----------------------------------------
    # Sections in spreadsheet order
    # Catching and Fielding appear side-by-side.
    # -----------------------------------------

    ordered_sections = sorted(
        sections.items(),
        key=lambda item: item[1]
    )


    for section_index, (
        section_name,
        start
    ) in enumerate(
        ordered_sections
    ):

        if (
            section_index + 1
            < len(ordered_sections)
        ):

            next_start = (
                ordered_sections[
                    section_index + 1
                ][1]
            )

        else:

            next_start = None


        section_rows = get_section_rows(
            rows,
            start,
            next_start
        )


        # Open the two-column layout
        # immediately before Catching.
        if section_name == "Catching":

            html_output += """
    <div class="small-stats-row">
"""


        html_output += f"""
    <section class="stats-section">

        <h2>
            {html_escape(section_name)}
        </h2>
"""


        html_output += make_table(
            section_rows,
            section_name
        )


        html_output += """
    </section>
"""


        # Close the two-column layout
        # immediately after Fielding.
        if section_name == "Fielding":

            html_output += """
    </div>
"""


    html_output += """
</div>

</body>

</html>
"""


    return html_output


def main():

    spreadsheet = get_google_sheet()

    # Get the shared Real Tm -> logo URL map.
    logo_map = get_logo_map(
        spreadsheet
    )

    for team_tab in TEAM_TABS:

        print(
            f"Generating team page: {team_tab}"
        )

        # Get this team's spreadsheet data.
        rows = get_team_data(
            spreadsheet,
            team_tab
        )

        # Download only logos needed by this team.
        download_required_logos(
            logo_map,
            rows
        )

        # Generate the team page.
        html_output = make_team_page(
            rows,
            team_tab
        )

        # Create the teams directory.
        os.makedirs(
            "teams",
            exist_ok=True
        )

        # Create a safe filename.
        filename = re.sub(
            r"[^a-z0-9]+",
            "-",
            team_tab.lower()
        ).strip("-")

        filepath = os.path.join(
            "teams",
            f"{filename}.html"
        )

        with open(
            filepath,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                html_output
            )

        print(
            f"Created {filepath}"
        )


if __name__ == "__main__":

    main()
