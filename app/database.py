from sqlalchemy.engine import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

drivername = os.getenv("DB_DRIVER", "postgresql")
username = os.getenv("DB_USER", "postgres")
host = os.getenv("DB_HOST", "localhost")  # Используем localhost или host.docker.internal
database = os.getenv("DB_NAME", "db_fastapi")
password = os.getenv("DB_PASSWORD", "postgres")

url_1 = URL.create(drivername=drivername, username=username, host=host, database=database, password=password)

# создаем движок - объект Engine
engine = create_engine(url_1)

# создаем базовую модель, от которой потом наследуются остальные модели
Base = declarative_base()

# создаем класс сессии
Session = sessionmaker(bind=engine)


# функция сессии
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
