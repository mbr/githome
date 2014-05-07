from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = sessionmaker()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    def __init__(self, name, **kwargs):
        name = name.lower()
        if not name.isalnum() or not name[0].isalpha():
            raise ValueError('Name must be alphanumeric and start with a '
                             'letter')
        super(User, self).__init__(name=name, **kwargs)
