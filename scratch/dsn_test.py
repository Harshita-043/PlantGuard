import psycopg, sys
url = "host=localhost port=5432 user=postgres password=harshita dbname=plantguard"
try:
    conn = psycopg.connect(url)
    print('Connected OK')
except Exception as e:
    print('Connect error:', e)

