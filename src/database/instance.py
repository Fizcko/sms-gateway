from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import create_database, database_exists
from environment.instance import database_config

mysql_uri = "mysql+pymysql://{}:{}@{}/{}?charset=utf8mb4".format(database_config['username'], database_config['password'], database_config['host'], database_config['database'])

if not database_exists(mysql_uri):
    create_database(mysql_uri)

engine = create_engine(mysql_uri, pool_recycle=3600, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

from contextlib import contextmanager

@contextmanager
def get_session():
    session = db_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

Base = declarative_base()

def init_db():
    import database.models
    Base.metadata.create_all(bind=engine)
