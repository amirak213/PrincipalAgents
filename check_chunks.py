import psycopg2
conn = psycopg2.connect("postgresql://dourbia:dourbia@localhost:5432/sig_dourbia")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM historical_chunks WHERE embedding IS NOT NULL")
print(cur.fetchone())
cur.execute("SELECT source_type, COUNT(*) FROM historical_chunks WHERE embedding IS NOT NULL GROUP BY source_type")
print(cur.fetchall())
