from app.core.config import settings
from app.core.debug import connection_check


def main():
    print("Checking Connection for Database Setup......")
    print("Owner Connection Status:", connection_check(settings.DB_OWNER_URL))
    print("Runtime Connection Status:", connection_check(settings.DB_RUNTIME_URL))
    print("Migrate Connection Status:", connection_check(settings.DB_MIGRATE_URL))



if __name__ == "__main__":
    main()
