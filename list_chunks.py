import psycopg2
conn = psycopg2.connect("postgresql://dourbia:dourbia@localhost:5432/sig_dourbia")
cur = conn.cursor()
cur.execute("SELECT id, title FROM historical_chunks WHERE embedding IS NOT NULL AND source_type='monument' ORDER BY id")
for row in cur.fetchall():
    print(row)
