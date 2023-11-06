from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from dotenv import load_dotenv
from datetime import datetime as dt
from os import getenv

# Замените следующие строки на реальные данные вашего подключения к PostgreSQL

load_dotenv()

engine = create_engine(getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(Integer, nullable=False, unique=True, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    registration_dt = Column(DateTime, nullable=False)
    shortcuts = relationship('Shortcut', back_populates='user')

    def __repr__(self):
        return f"<User(username='{self.username}', telegram_id='{self.telegram_id}')>"

class Shortcut(Base):
    __tablename__ = 'shortcuts'

    telegram_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    id = Column(Integer, primary_key=True)
    shortcut_name = Column(String, index=True, nullable=False)
    content_type = Column(String, nullable=False)
    text = Column(String, nullable=True)
    content = Column(String, nullable=True)
    add_dt = Column(DateTime, nullable=False)
    update_dt = Column(DateTime, nullable=False)
    user = relationship('User', back_populates='shortcuts')

    def __repr__(self):
        return f"<Shortcut(keyword='{self.keyword}', content='{self.content[:10]}...')>"

# Создать все таблицы
Base.metadata.create_all(engine)

# Функции для взаимодействия с базой данных

def create_user(telegram_id: int, username: str):
    with Session() as session:
        user = User(username=username, telegram_id=telegram_id, registration_dt=dt.now())
        session.add(user)
        session.commit()

def get_user(telegram_id: int):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        return user

def add_shortcut(shortcut_name: str, telegram_id: int, content_type: str, text: str, content: str):
    session = Session()
    shortcut = Shortcut(
        shortcut_name=shortcut_name, 
        telegram_id=telegram_id,
        content_type=content_type,
        text=text,
        content=content,
        add_dt=dt.now(),
        update_dt=dt.now()
    )
    session.add(shortcut)
    session.commit()
    session.close()

def get_shortcuts(telegram_id):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    shortcuts = user.shortcuts if user else []
    session.close()
    return shortcuts

def get_shortcut(telegram_id, shortcut_name):
    with Session() as session:
        shortcut = session.query(Shortcut).filter_by(telegram_id=telegram_id, shortcut_name=shortcut_name).first()
        return shortcut

def update_shortcut(shortcut_id: int, new_shortcut_name: str, telegram_id: int, new_content_type: str, new_text: str, new_content: str):
    with Session() as session:
        shortcut = session.query(Shortcut).filter_by(id=shortcut_id).first()
        if shortcut:
            shortcut.shortcut_name = new_shortcut_name
            shortcut.content_type = new_content_type
            shortcut.text = new_text
            shortcut.content = new_content
            session.commit()

def delete_shortcut(shortcut_id):
    with Session() as session:
        shortcut = session.query(Shortcut).filter_by(id=shortcut_id).first()
        if shortcut:
            session.delete(shortcut)
            session.commit()
