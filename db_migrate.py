from app import app,db

"""
This script is used to migrate the database schema to latest models.
For example, when trivia's table is added, this script is used to create the table in the database.
If a field is added in db, currently i'm not sure it can be used for migration.
"""
with app.app_context():
    db.create_all()
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print("Tables in the database:", tables)