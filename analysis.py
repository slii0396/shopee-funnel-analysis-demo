"""Synthetic e-commerce funnel analysis using SQLite.

The generated data are deliberately synthetic and are not Shopee internal data.
"""

import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def build_sessions():
    channels = (
        [("recommendation", 200, 28), ("search", 300, 30),
         ("ads", 250, 20), ("direct", 250, 15)]
    )
    sessions, session_id = [], 1
    for channel, count, orders in channels:
        for index in range(count):
            device = "mobile" if session_id <= 512 else "desktop"
            sessions.append({
                "session_id": session_id,
                "channel": channel,
                "device": device,
                "added_to_cart": int(index < max(orders * 3, count // 4)),
                "ordered": int(index < orders),
                "single_page_exit": int(device == "mobile" and session_id <= 236),
                "cta_clicked": int(index % 3 != 0),
            })
            session_id += 1
    return sessions


def query_rows(connection, sql):
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    return columns, cursor.fetchall()


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def main():
    sessions = build_sessions()
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE sessions (
        session_id INTEGER PRIMARY KEY,
        channel TEXT, device TEXT,
        added_to_cart INTEGER, ordered INTEGER,
        single_page_exit INTEGER, cta_clicked INTEGER
        )"""
    )
    connection.executemany(
        "INSERT INTO sessions VALUES (:session_id, :channel, :device, :added_to_cart, :ordered, :single_page_exit, :cta_clicked)",
        sessions,
    )

    channel_sql = """
    SELECT channel, COUNT(*) AS visits,
           SUM(added_to_cart) AS carts,
           SUM(ordered) AS orders,
           ROUND(100.0 * SUM(ordered) / COUNT(*), 1) AS order_rate_pct
    FROM sessions GROUP BY channel ORDER BY order_rate_pct DESC
    """
    device_sql = """
    SELECT device, COUNT(*) AS visits,
           SUM(single_page_exit) AS single_page_exits,
           ROUND(100.0 * SUM(single_page_exit) / COUNT(*), 1) AS exit_rate_pct,
           ROUND(100.0 * SUM(cta_clicked) / COUNT(*), 1) AS cta_rate_pct
    FROM sessions GROUP BY device ORDER BY device
    """
    channel_columns, channel_rows = query_rows(connection, channel_sql)
    device_columns, device_rows = query_rows(connection, device_sql)

    RESULTS.mkdir(exist_ok=True)
    write_csv(RESULTS / "channel_metrics.csv", channel_columns, channel_rows)
    write_csv(RESULTS / "device_metrics.csv", device_columns, device_rows)

    recommendation_rate = next(row[4] for row in channel_rows if row[0] == "recommendation")
    mobile_exit_rate = next(row[3] for row in device_rows if row[0] == "mobile")
    summary = (
        f"Synthetic sessions: {len(sessions)}\n"
        f"Recommendation order rate: {recommendation_rate:.1f}%\n"
        f"Mobile single-page exit rate: {mobile_exit_rate:.1f}%\n"
        "Boundary: synthetic demonstration only; not real Shopee data.\n"
    )
    (RESULTS / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    assert recommendation_rate == 14.0
    assert mobile_exit_rate == 46.1
    print("Reproducibility check: PASS")


if __name__ == "__main__":
    main()

