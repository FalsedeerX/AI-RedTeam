from app.core.config import settings


def main():
    print(settings.DB_MASTER_URL)
    print(settings.DB_RUNTIME_URL)
    print(settings.DB_ALEMBIC_URL)



if __name__ == "__main__":
    main()
