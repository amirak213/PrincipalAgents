import psycopg2
conn = psycopg2.connect("postgresql://dourbia:dourbia@localhost:5433/dourbia")
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='monuments' ORDER BY ordinal_position;")
for r in cur.fetchall():
    print(r)
