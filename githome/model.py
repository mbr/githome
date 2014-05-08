from binascii import hexlify

from paramiko.rsakey import RSAKey
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import sessionmaker, relationship
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


class PublicKey(Base):
    __tablename__ = 'public_key'

    fingerprint = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), primary_key=True)
    user = relationship(User, backref='public_keys')
    data = Column(LargeBinary, nullable=False)

    def __init__(self, data, user=None):
        self.data = data
        self.fingerprint = hexlify(self.pkey.get_fingerprint())
        self.user = user

    @property
    def pkey(self):
        if not hasattr(self, '_pkey'):
            self._pkey = RSAKey(data=self.data)
        return self._pkey
