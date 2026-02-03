import sqlite3

conn = sqlite3.connect("data/digest.db")
count = conn.execute("select count(*) from items").fetchone()[0]
print("Items in DB:", count)

rows = conn.execute(
    "select source, title, url from items order by created_at desc limit 5"
).fetchall()

print("\nLatest 5 items:")
for r in rows:
    print("-", r[1])
