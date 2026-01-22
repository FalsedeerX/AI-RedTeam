from app.core.config import settings


def main():
    print(settings.ALEMBIC_DB_URL)
    print(settings.DB_URL)



if __name__ == "__main__":
    main()
