import os
import json
import html
import re
import urllib.request
import csv

import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# SETTINGS
# ============================================================

SPREADSHEET_ID = (
    "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"
)

OUTPUT_FILE = "batting-stats.html"

LOGO_DIRECTORY = "logos"


# ============================================================
# TEAM TABS
# ============================================================

TEAM_TABS = [
    "Iowa",
    "Omaha",
    "Richmond",
    "Pawtucket",
    "Dunedin",
    "Portland"
    # Add the rest of your team tab names here
]


# ============================================================
# GOOGLE SHEETS
# ============================================================

def get_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT"]
    )

    credentials = (
        Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
    )

    client = gspread.authorize(
        credentials
    )

    return client.open_by_key(
        SPREADSHEET_ID
    )


# ============================================================
# HTML ESCAPE
# ============================================================

def html_escape(value):

    return html.escape(
        str(value),
        quote=True
    )


# ============================================================
# GET TEAM DATA
# ============================================================

def get_team_data(
    spreadsheet,
    team_tab
):

    worksheet = spreadsheet.worksheet(
        team_tab
    )

    return worksheet.get_all_values()


# ============================================================
# LOGO MAP
#
# This is the same logo-map system used by team-stats.py.
# ============================================================

def get_logo_map(
    spreadsheet
):

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


        start = image_formula.find(
            '"'
        )

        end = image_formula.rfind(
            '"'
        )


        if start == -1 or end <= start:

            continue


        logo_url = image_formula[
            start + 1:end
        ]


        if logo_url:

            logo_map[
                real_team
            ] = logo_url


    return logo_map


# ============================================================
# LOGO FILENAME
# ============================================================

def make_logo_filename(
    real_team
):

    filename = real_team.lower()


    filename = re.sub(
        r"[^a-z0-9]+",
        "-",
        filename
    )


    filename = filename.strip(
        "-"
    )


    return filename + ".gif"


# ============================================================
# DOWNLOAD REQUIRED LOGOS
#
# This is the same approach used by team-stats.py.
#
# Existing logos are NOT downloaded again.
# ============================================================

def download_required_logos(
    logo_map,
    all_team_rows
):

    os.makedirs(
        LOGO_DIRECTORY,
        exist_ok=True
    )


    required_teams = set()


    for rows in all_team_rows:

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


            request = (
                urllib.request.Request(
                    logo_url,
                    headers={
                        "User-Agent":
                            "Mozilla/5.0"
                    }
                )
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


# ============================================================
# FIND BATTING SECTION
# ============================================================

def find_batting_section(
    rows
):

    for index, row in enumerate(
        rows
    ):

        values = [
            cell.strip()
            for cell in row
        ]


        if "Batting" in values:

            return index


    return None


# ============================================================
# GET BATTING ROWS
# ============================================================

def get_batting_rows(
    rows
):

    batting_start = (
        find_batting_section(
            rows
        )
    )


    if batting_start is None:

        return []


    start = batting_start + 1


    # Find the next major section.

    end = len(rows)


    for index in range(
        start,
        len(rows)
    ):

        values = [
            cell.strip()
            for cell in rows[index]
        ]


        if (
            "Pitching" in values
            or
            "Catching" in values
            or
            "Fielding" in values
        ):

            end = index

            break


    section = rows[
        start:end
    ]


    # Remove blank rows from beginning.

    while (
        section
        and not any(
            cell.strip()
            for cell in section[0]
        )
    ):

        section.pop(0)


    # Remove blank rows from end.

    while (
        section
        and not any(
            cell.strip()
            for cell in section[-1]
        )
    ):

        section.pop()


    return section


# ============================================================
# FORMAT FRACTIONS
# ============================================================

def format_display_value(
    value
):

    display_value = html_escape(
        value
    )


    display_value = display_value.replace(
        " 1/3",
        '<span class="fraction">¹⁄₃</span>'
    )


    display_value = display_value.replace(
        " 2/3",
        '<span class="fraction">²⁄₃</span>'
    )


    return display_value


# ============================================================
# MAKE BATTING TABLE
# ============================================================

def make_batting_table(
    players
):

    if not players:

        return """
        <p>No batting data found.</p>
        """


    header = players[0]["header"]


    # --------------------------------------------------------
    # Find final used spreadsheet column.
    # --------------------------------------------------------

    last_column = 0


    for player in players:

        row = player["row"]


        for index, value in enumerate(
            row
        ):

            if value.strip():

                last_column = max(
                    last_column,
                    index
                )


    header = header[
        :last_column + 1
    ]


    # --------------------------------------------------------
    # Find Real Tm.
    #
    # Team spreadsheets use Column C for Real Tm.
    # --------------------------------------------------------

    real_team_column = 2


    html_output = """
    <div class="table-wrapper">

        <table
            class="team-stats-table"
            id="batting-stats-table"
        >

            <thead>

                <tr>

                    <th
                        class="sortable team-column"
                        data-column="team"
                    >
                        Team
                    </th>


                    <th
                        class="logo-header"
                    >
                    </th>
    """


    # --------------------------------------------------------
    # Same batting columns as team-stats.py.
    #
    # Skip spreadsheet Column A because it is reserved
    # for the logo.
    # --------------------------------------------------------

    for column_index, value in enumerate(
        header[1:],
        start=1
    ):

        html_output += f"""
                    <th
                        class="sortable"
                        data-column="{column_index}"
                    >
                        {html_escape(value)}
                    </th>
        """


    html_output += """
                </tr>

            </thead>


            <tbody>
    """


    # ========================================================
    # PLAYER ROWS
    # ========================================================

    for player in players:

        row = player["row"]


        # ----------------------------------------------------
        # Skip Team Totals.
        #
        # Column B is row[1].
        # ----------------------------------------------------

        if (
            len(row) > 1
            and row[1].strip()
            == "Team Totals"
        ):

            continue


        html_output += """
                <tr>
        """


        # ----------------------------------------------------
        # TEAM
        # ----------------------------------------------------

        html_output += f"""
                    <td class="team-column">
                        {html_escape(player["team"])}
                    </td>
        """


        # ----------------------------------------------------
        # LOGO
        # ----------------------------------------------------

        logo_filename = ""


        if (
            real_team_column
            < len(row)
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


        if logo_filename:

            html_output += f"""
                    <td class="logo-cell">

                        <img
                            src="logos/{html_escape(logo_filename)}"
                            class="player-logo"
                            alt=""
                        >

                    </td>
            """

        else:

            html_output += """
                    <td class="logo-cell"></td>
            """


        # ----------------------------------------------------
        # Spreadsheet data.
        #
        # Start with Column B, exactly like team-stats.py.
        # ----------------------------------------------------

        for value in row[1:]:

            display_value = (
                format_display_value(
                    value
                )
            )


            html_output += (
                f"<td>{display_value}</td>"
            )


        # ----------------------------------------------------
        # Fill missing cells.
        # ----------------------------------------------------

        expected_cells = (
            len(header) + 1
        )


        actual_cells = (
            len(row) + 2
        )


        missing = (
            expected_cells
            - actual_cells
        )


        for _ in range(
            max(0, missing)
        ):

            html_output += (
                "<td></td>"
            )


        html_output += """
                </tr>
        """


    html_output += """
            </tbody>

        </table>

    </div>
    """


    return html_output


# ============================================================
# MAKE PAGE
# ============================================================

def make_page(
    players
):

    html_output = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>


<title>
    Batting Stats - Strat-o-Matic
</title>


<link
    rel="preconnect"
    href="https://fonts.googleapis.com"
>


<link
    rel="preconnect"
    href="https://fonts.googleapis.com"
    crossorigin
>


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


    h1 {

        font-size: 32px;

        font-weight: 700;

        margin: 0 0 20px 0;
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


    .team-stats-table th {

        font-weight: 600;

        border-bottom: 1px solid #222;

        user-select: none;
    }


    .team-stats-table
    tbody tr:last-child {

        border-bottom: 1px solid #222;
    }


    .team-stats-table
    tbody tr:hover {

        background: #f5f5f5;
    }


    /* =========================
       SORTING
       ========================= */

    .sortable {

        cursor: pointer;
    }


    .sortable::after {

        content: " ↕";

        font-size: 10px;

        color: #888;
    }


    .sortable.sort-ascending::after {

        content: " ▲";

        color: #111;
    }


    .sortable.sort-descending::after {

        content: " ▼";

        color: #111;
    }


    /* =========================
       TEAM COLUMN
       ========================= */

    .team-column {

        text-align: left !important;

        font-weight: 600;
    }


    /* =========================
       LOGOS
       ========================= */

    .logo-header,
    .logo-cell {

        width: 28px;

        padding-left: 2px !important;

        padding-right: 2px !important;

        text-align: center !important;
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
       MOBILE
       ========================= */

    @media (max-width: 900px) {

        body {

            padding: 15px;
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

    }

</style>

</head>


<body>

<div class="container">

    <h1>
        Batting Stats
    </h1>
    """


    html_output += make_batting_table(
        players
    )


    html_output += """

</div>


<script>

document.addEventListener(
    "DOMContentLoaded",
    function() {

        const table =
            document.getElementById(
                "batting-stats-table"
            );


        if (!table) {

            return;
        }


        const headers =
            table.querySelectorAll(
                "thead th.sortable"
            );


        headers.forEach(
            function(header) {

                header.addEventListener(
                    "click",
                    function() {

                        const column =
                            header.dataset.column;


                        const tbody =
                            table.querySelector(
                                "tbody"
                            );


                        const rows =
                            Array.from(
                                tbody.querySelectorAll(
                                    "tr"
                                )
                            );


                        const descending =
                            header.classList.contains(
                                "sort-ascending"
                            );


                        headers.forEach(
                            function(other) {

                                other.classList.remove(
                                    "sort-ascending"
                                );

                                other.classList.remove(
                                    "sort-descending"
                                );

                            }
                        );


                        header.classList.add(
                            descending
                                ? "sort-descending"
                                : "sort-ascending"
                        );


                        rows.sort(
                            function(a, b) {

                                let aValue;
                                let bValue;


                                if (
                                    column === "team"
                                ) {

                                    aValue =
                                        a.children[0]
                                            .textContent
                                            .trim();

                                    bValue =
                                        b.children[0]
                                            .textContent
                                            .trim();

                                } else {

                                    /*
                                     * HTML columns:
                                     *
                                     * 0 = Team
                                     * 1 = Logo
                                     * 2 = Spreadsheet Column B
                                     * 3 = Spreadsheet Column C
                                     * etc.
                                     *
                                     * data-column is based on
                                     * the spreadsheet columns
                                     * after Column A.
                                     */

                                    const spreadsheetColumn =
                                        parseInt(
                                            column
                                        );


                                    const htmlColumn =
                                        spreadsheetColumn
                                        + 1;


                                    aValue =
                                        a.children[
                                            htmlColumn
                                        ]
                                            .textContent
                                            .trim();

                                    bValue =
                                        b.children[
                                            htmlColumn
                                        ]
                                            .textContent
                                            .trim();

                                }


                                const aNumber =
                                    parseFloat(
                                        aValue
                                            .replace(
                                                /,/g,
                                                ""
                                            )
                                    );


                                const bNumber =
                                    parseFloat(
                                        bValue
                                            .replace(
                                                /,/g,
                                                ""
                                            )
                                    );


                                let comparison;


                                if (
                                    !isNaN(aNumber)
                                    &&
                                    !isNaN(bNumber)
                                ) {

                                    comparison =
                                        aNumber
                                        - bNumber;

                                } else {

                                    comparison =
                                        aValue.localeCompare(
                                            bValue
                                        );

                                }


                                if (
                                    descending
                                ) {

                                    comparison *= -1;

                                }


                                return comparison;

                            }
                        );


                        rows.forEach(
                            function(row) {

                                tbody.appendChild(
                                    row
                                );

                            }
                        );

                    }
                );

            }
        );

    }
);

</script>


</body>

</html>
    """


    return html_output


# ============================================================
# MAIN
# ============================================================

def main():

    spreadsheet = get_google_sheet()


    all_team_rows = []


    all_players = []


    # --------------------------------------------------------
    # Read every team.
    # --------------------------------------------------------

    for team_tab in TEAM_TABS:

        print(
            f"Reading batting stats: {team_tab}"
        )


        rows = get_team_data(
            spreadsheet,
            team_tab
        )


        all_team_rows.append(
            rows
        )


        batting_rows = get_batting_rows(
            rows
        )


        if len(batting_rows) < 2:

            print(
                f"No batting data found: "
                f"{team_tab}"
            )

            continue


        header = batting_rows[0]


        data_rows = batting_rows[1:]


        # ----------------------------------------------------
        # Determine final used column.
        # ----------------------------------------------------

        last_column = 0


        for row in batting_rows:

            for index, value in enumerate(
                row
            ):

                if value.strip():

                    last_column = max(
                        last_column,
                        index
                    )


        header = header[
            :last_column + 1
        ]


        for row in data_rows:

            row = row[
                :last_column + 1
            ]


            if not any(
                value.strip()
                for value in row
            ):

                continue


            # Skip Team Totals.
            if (
                len(row) > 1
                and row[1].strip()
                == "Team Totals"
            ):

                continue


            # Skip rows without a player name.
            if (
                len(row) <= 1
                or not row[1].strip()
            ):

                continue


            all_players.append(
                {
                    "team": team_tab,
                    "header": header,
                    "row": row
                }
            )


    # --------------------------------------------------------
    # Get logo map and download any missing logos.
    # --------------------------------------------------------

    logo_map = get_logo_map(
        spreadsheet
    )


    download_required_logos(
        logo_map,
        all_team_rows
    )


    # --------------------------------------------------------
    # Generate page.
    # --------------------------------------------------------

    html_output = make_page(
        all_players
    )


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            html_output
        )


    # ============================================================
    # SAVE PROCESSED BATTING DATA FOR OTHER PAGES
    # ============================================================

    CSV_FILE = "batting-stats.csv"

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.writer(csv_file)

        writer.writerow([
            "Team",
            "LOGO",
            "Name",
            "Real Tm",
            "POS",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "G",
            "PA",
            "AB",
            "R",
            "H",
            "2b",
            "3b",
            "HR",
            "RBI",
            "XBH",
            "TB",
            "SB",
            "CS",
            "SO",
            "BB",
            "HBP",
            "GIDP",
            "OPS+",
            "WOBA",
            "BABIP",
            "K%",
            "BB%",
            "AB/HR",
            "ISO",
            "WRC+",
            "RC/G"
        ])

        for player in all_players:
    
            row = player["row"]
            header = player["header"]
            team = player["team"]
    
            # Create a lookup from column name to column position.
            column_map = {}
    
            for index, column in enumerate(header):
    
                column_map[
                    column.strip()
                ] = index
    
    
            def get_value(column_name):
    
                index = column_map.get(
                    column_name
                )
    
                if index is None:
                    return ""
    
                if index >= len(row):
                    return ""
    
                return row[index].strip()
    
    
            writer.writerow([
                team,
                "",
                get_value("Name"),
                get_value("Real Tm"),
                get_value("POS"),
                get_value("AVG"),
                get_value("OBP"),
                get_value("SLG"),
                get_value("OPS"),
                get_value("G"),
                get_value("PA"),
                get_value("AB"),
                get_value("R"),
                get_value("H"),
                get_value("2b"),
                get_value("3b"),
                get_value("HR"),
                get_value("RBI"),
                get_value("XBH"),
                get_value("TB"),
                get_value("SB"),
                get_value("CS"),
                get_value("SO"),
                get_value("BB"),
                get_value("HBP"),
                get_value("GIDP"),
                get_value("OPS+"),
                get_value("WOBA"),
                get_value("BABIP"),
                get_value("K%"),
                get_value("BB%"),
                get_value("AB/HR"),
                get_value("ISO"),
                get_value("WRC+"),
                get_value("RC/G")
            ])


    print(
        f"Created {OUTPUT_FILE} "
        f"with {len(all_players)} players."
    )

    print(
        f"Created {CSV_FILE} "
        f"with {len(all_players)} players."
    )


if __name__ == "__main__":

    main()
