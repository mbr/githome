from binascii import hexlify

from sqlacfg import ConfigSettingMixin
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sshkeys import Key as SSHKey


Base = declarative_base()
Session = sessionmaker()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    def __init__(self, name, **kwargs):
        name = name.lower()
        if not name.isalnum() or not name[0].isalpha():
            raise ValueError('Name must be alphanumeric and start with a '
                             'letter')
        super(User, self).__init__(name=name, **kwargs)


class PublicKey(Base):
    __tablename__ = 'public_keys'

    fingerprint = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(User,
                        backref=backref('public_keys', cascade=
                                        'all, delete-orphan'))
    data = Column(LargeBinary, nullable=False)

    @classmethod
    def from_pkey(cls, pkey):
        return cls(data=pkey.data, fingerprint=hexlify(pkey.fingerprint))

    def as_pkey(self, comment=None, options=None):
        return SSHKey(self.data, comment, options)


class ConfigSetting(Base, ConfigSettingMixin):
    __tablename__ = 'config'
