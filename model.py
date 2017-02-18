from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, func
from passlib.apps import custom_app_context as pwd_context
import random, string

Base = declarative_base()
engine = create_engine('sqlite:///database.db')
Base.metadata.create_all(engine)

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    facebook_id = Column(Integer)
    location = Column(String)
    hometown = Column(String)
    languages = relationship('LanguageAssociation', back_populates='user')
    learningLanguages = relationship('LearningLanguageAssociation', back_populates='user')

class Language(Base):
    __tablename__ = 'language'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    language_id = Column(Integer, unique=True)
    users = relationship('LanguageAssociation', back_populates='language')
    learningUsers = relationship('LearningLanguageAssociation', back_populates='language')

class LanguageAssociation(Base):
    __tablename__ = 'languageAssociation'
    language_id = Column(Integer, ForeignKey('language.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    language = relationship('Language', back_populates='users')
    user = relationship('User', back_populates='languages')

class LearningLanguageAssociation(Base):
    __tablename__ = 'learningLanguageAssociation'
    language_id = Column(Integer, ForeignKey('language.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    language = relationship('Language', back_populates='learningUsers')
    user = relationship('User', back_populates='learningLanguages')
