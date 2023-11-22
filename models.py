from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from dotenv import load_dotenv
from datetime import datetime as dt
from os import getenv

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
    start_param = Column(String, nullable=True)

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
    entities = Column(JSON, nullable=True)
    num_of_uses = Column(Integer, default=0)
    last_use_dt = Column(DateTime, nullable=True)
    user = relationship('User', back_populates='shortcuts')

    def __repr__(self):
        return f"<Shortcut(shortcut_name='{self.shortcut_name}', content='{self.text[:10]}...')>"

class Admin(Base):
    __tablename__ = 'admins'
    
    telegram_id = Column(Integer, nullable=False, primary_key=True)

    def __repr__(self):
        return f"<Admin(telegram_id='{self.telegram_id}')>"

# Создать все таблицы
Base.metadata.create_all(engine)

# Функции для взаимодействия с базой данных

def create_user(telegram_id: int, username: str, start_param: str=None):
    with Session() as session:
        user = User(username=username, telegram_id=telegram_id, registration_dt=dt.now(), start_param=start_param)
        session.add(user)
        session.commit()

def get_user(telegram_id: int):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        return user

def add_shortcut(shortcut_name: str, telegram_id: int, content_type: str, text: str, content: str, entities: list=None):
    with Session() as session:
        shortcut = Shortcut(
            shortcut_name=shortcut_name, 
            telegram_id=telegram_id,
            content_type=content_type,
            text=text,
            content=content,
            add_dt=dt.now(),
            update_dt=dt.now(),
            entities=entities or []
        )
        session.add(shortcut)
        session.commit()

def get_shortcuts(telegram_id):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        shortcuts = user.shortcuts if user else []
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

def get_users_list() -> dict:
    with Session() as session:
        users = (
            session.query(
                User.telegram_id,
                User.registration_dt,
                User.username,
                User.start_param,
                func.count(
                    Shortcut.id.distinct()
                ).label(
                    'num_shortcuts'
                )
            ).outerjoin(
                Shortcut
            ).group_by(
                User.telegram_id, 
                User.registration_dt, 
                User.username,
                User.start_param
            ).order_by(
                User.registration_dt
            )
        )
        return {user.username or str(user.telegram_id): (user.registration_dt, user.num_shortcuts, user.start_param) for user in users}

def increase_chosen_result_counter(shortcut_id: int):
    with Session() as session:
        shortcut = session.query(Shortcut).filter_by(id=shortcut_id).first()
        if shortcut:
            shortcut.num_of_uses += 1
            shortcut.last_use_dt = dt.now()
            session.commit()
    

def is_admin(telegram_id: int) -> bool:
    with Session() as session:
        admin = session.query(Admin).filter_by(telegram_id=telegram_id).first()
        return admin is not None
