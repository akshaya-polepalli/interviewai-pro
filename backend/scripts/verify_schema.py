"""Print public tables and seed counts — run inside API container."""

from sqlalchemy import text

from app.database.session import engine


def main() -> None:
    with engine.connect() as conn:
        tables = conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY 1"
            )
        ).fetchall()
        print(f"TABLES ({len(tables)}):")
        for (name,) in tables:
            print(f"  - {name}")

        roles = conn.execute(text("SELECT name FROM roles ORDER BY name")).fetchall()
        print("ROLES:", [r[0] for r in roles])
        print("PERMISSIONS:", conn.execute(text("SELECT count(*) FROM permissions")).scalar())
        print("ACHIEVEMENTS:", conn.execute(text("SELECT count(*) FROM achievements")).scalar())


if __name__ == "__main__":
    main()
