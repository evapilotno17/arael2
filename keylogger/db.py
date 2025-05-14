from pathlib import Path
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# locate ../keydb/keys.db   (one level up from keylogger/)
db_file = (Path(__file__).parent.parent / "keydb" / "keys.db").resolve()
DB_PATH = f"sqlite:///{db_file}"

engine       = create_engine(DB_PATH, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()


class Keystroke(Base):
    __tablename__ = "keystrokes"

    ts_us = Column(Integer, primary_key=True, index=True)
    code  = Column(Integer, nullable=False)
    os    = Column(String,  nullable=False)


def init_db() -> None:
    """create the table if the C loggers havent already."""
    Base.metadata.create_all(bind=engine)
