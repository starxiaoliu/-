from pathlib import Path
import os
from uuid import uuid4
from sqlalchemy import create_engine, String, Integer, JSON, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATA = Path(os.environ.get('DATA_DIR', str(Path(__file__).resolve().parents[2] / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'uploads').mkdir(exist_ok=True)
engine = create_engine(f'sqlite:///{DATA / "review.sqlite3"}', connect_args={'check_same_thread': False})
@event.listens_for(engine, 'connect')
def pragma(db, _):
    db.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine)
class Base(DeclarativeBase): pass
class Paper(Base):
    __tablename__ = 'papers'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str]
    sha256: Mapped[str] = mapped_column(String, unique=True)
    page_count: Mapped[int]
    parse_status: Mapped[str] = mapped_column(default='needs_review')
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    parser_version: Mapped[str] = mapped_column(default='fenbi-layout-0.1')
    collection_kind: Mapped[str] = mapped_column(default='full')
    expected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
class Question(Base):
    __tablename__ = 'questions'
    __table_args__ = (UniqueConstraint('paper_id', 'number'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    paper_id: Mapped[str] = mapped_column(ForeignKey('papers.id', ondelete='CASCADE'))
    number: Mapped[int]
    module: Mapped[str] = mapped_column(default='待核对')
    subtype: Mapped[str] = mapped_column(default='')
    page_start: Mapped[int]
    page_end: Mapped[int]
    correct_answer: Mapped[str | None]
    user_answer: Mapped[str | None]
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(default='low')
class Tag(Base):
    __tablename__ = 'tags'
    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str]
    module: Mapped[str]
    subtype: Mapped[str]
    origin: Mapped[str] = mapped_column(default='system')
class Review(Base):
    __tablename__ = 'reviews'
    question_id: Mapped[str] = mapped_column(ForeignKey('questions.id', ondelete='CASCADE'), primary_key=True)
    status: Mapped[str] = mapped_column(default='not_started')
    attempt_flags: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(default='')
    correct_method: Mapped[str] = mapped_column(default='')
    next_time_rule: Mapped[str] = mapped_column(default='')
    review_later: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[str] = mapped_column(default='')
class ReviewTag(Base):
    __tablename__ = 'review_tags'
    question_id: Mapped[str] = mapped_column(ForeignKey('reviews.question_id', ondelete='CASCADE'), primary_key=True)
    tag_code: Mapped[str] = mapped_column(ForeignKey('tags.code'), primary_key=True)
