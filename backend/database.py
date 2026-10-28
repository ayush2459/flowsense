import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DB_AUTH_MODE = os.getenv("DB_AUTH_MODE", "").strip().lower()

if DB_AUTH_MODE == "iam":
    import boto3
    from sqlalchemy import URL, event

    AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "flowsense")
    DB_USER = os.getenv("DB_USER", "flowsense_gateway")

    if not DB_HOST or not DB_USER:
        raise RuntimeError(
            "DB_HOST and DB_USER are required when DB_AUTH_MODE=iam."
        )

    rds_client = boto3.client("rds", region_name=AWS_REGION)

    engine = create_engine(
        URL.create(
            "postgresql+psycopg2",
            username=DB_USER,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            query={"sslmode": "require"},
        ),
        pool_pre_ping=True,
        pool_recycle=840,
        pool_size=10,
        max_overflow=20,
        future=True,
    )

    @event.listens_for(engine, "do_connect")
    def add_iam_token(dialect, connection_record, cargs, cparams):
        cparams["password"] = rds_client.generate_db_auth_token(
            DBHostname=DB_HOST,
            Port=DB_PORT,
            DBUsername=DB_USER,
        )

else:
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise RuntimeError(
            "Set DATABASE_URL or configure DB_AUTH_MODE=iam."
        )

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=840,
        pool_size=10,
        max_overflow=20,
        future=True,
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
