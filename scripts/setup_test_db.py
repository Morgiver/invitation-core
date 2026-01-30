"""Setup test databases for invitation-core.

This script creates test databases for PostgreSQL and MongoDB.
"""

import argparse
import sys


def setup_postgresql(host: str, port: int, username: str, password: str, db_name: str):
    """Setup PostgreSQL test database."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=host, port=port, user=username, password=password, dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Drop database if exists
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        print(f"[PostgreSQL] Dropped existing database: {db_name}")

        # Create database
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"[PostgreSQL] Created database: {db_name}")

        cursor.close()
        conn.close()

        # Create tables
        from sqlalchemy import create_engine

        from invitation_core.adapters.repositories.sqlalchemy import create_tables

        connection_string = (
            f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
        )
        engine = create_engine(connection_string)
        create_tables(engine)
        print(f"[PostgreSQL] Created tables in database: {db_name}")

        print(f"\n[SUCCESS] PostgreSQL setup complete!")
        print(f"Connection string: {connection_string}")
        print(f"\nSet environment variable:")
        print(f'export TEST_DB_CONNECTION_STRING="{connection_string}"')

    except Exception as e:
        print(f"[ERROR] Failed to setup PostgreSQL: {e}", file=sys.stderr)
        sys.exit(1)


def setup_mongodb(host: str, port: int, username: str, password: str, db_name: str):
    """Setup MongoDB test database."""
    from pymongo import MongoClient

    try:
        # Connect to MongoDB
        if username and password:
            connection_string = (
                f"mongodb://{username}:{password}@{host}:{port}/"
            )
        else:
            connection_string = f"mongodb://{host}:{port}/"

        client = MongoClient(connection_string)

        # Drop database if exists
        client.drop_database(db_name)
        print(f"[MongoDB] Dropped existing database: {db_name}")

        # Create database and collection (indexes will be created automatically)
        db = client[db_name]
        db.create_collection("invitations")
        print(f"[MongoDB] Created database: {db_name}")

        client.close()

        print(f"\n[SUCCESS] MongoDB setup complete!")
        print(f"Connection string: {connection_string}")
        print(f"\nSet environment variables:")
        print(f'export TEST_MONGO_CONNECTION_STRING="{connection_string}"')
        print(f'export TEST_MONGO_DB_NAME="{db_name}"')

    except Exception as e:
        print(f"[ERROR] Failed to setup MongoDB: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup test databases for invitation-core")
    parser.add_argument(
        "--db-type",
        choices=["postgresql", "mongodb"],
        required=True,
        help="Database type to setup",
    )
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", type=int, help="Database port")
    parser.add_argument("--username", help="Database username")
    parser.add_argument("--password", help="Database password")
    parser.add_argument(
        "--db-name",
        default="test_invitation_core",
        help="Database name (default: test_invitation_core)",
    )

    args = parser.parse_args()

    # Set default ports
    if args.port is None:
        args.port = 5432 if args.db_type == "postgresql" else 27017

    if args.db_type == "postgresql":
        if not args.username or not args.password:
            print("[ERROR] PostgreSQL requires --username and --password", file=sys.stderr)
            sys.exit(1)
        setup_postgresql(args.host, args.port, args.username, args.password, args.db_name)
    elif args.db_type == "mongodb":
        setup_mongodb(args.host, args.port, args.username, args.password, args.db_name)


if __name__ == "__main__":
    main()
