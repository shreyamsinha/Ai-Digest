import sqlite3

conn = sqlite3.connect("data/digest.db")
rows = conn.execute("select name from sqlite_master where type='table'")
print([r[0] for r in rows])
