import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute("DELETE FROM django_migrations WHERE app='herramienta'")
c.execute("DELETE FROM django_migrations WHERE app='almacen'")
c.execute("DELETE FROM django_migrations WHERE app='prestamo'")
c.execute("DELETE FROM django_migrations WHERE app='pagina_principal'")
conn.commit()
conn.close()
