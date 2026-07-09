import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="admin",
    password="Lty120712!",
    dbname="SPRIDS_agent"
)
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
tables = [row[0] for row in cur.fetchall()]
print("\n".join(tables))
cur.close()
conn.close()
