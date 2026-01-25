from app.core.config import settings
from app.core.debug import connection_check


def main():
    print("Checking Connection for Database Setup......")
    print("Connection Status:", connection_check(settings.DB_ALEMBIC_URL))



if __name__ == "__main__":
    main()
