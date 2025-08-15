# app/database.py

import json
from sqlalchemy import create_engine, Column, String, Text, PrimaryKeyConstraint, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from .utils import normalize_subject

DATABASE_URL = "sqlite:///./conversations.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    prospect_email = Column(String, primary_key=True, index=True)
    # Add subject to uniquely identify a conversation thread
    subject = Column(String, primary_key=True, index=True)
    conversation_history = Column(Text, default="[]")
    # Flag to track if research has been performed for this thread.
    research_performed = Column(Boolean, default=False, nullable=False)

    # Define a composite primary key
    __table_args__ = (PrimaryKeyConstraint('prospect_email', 'subject'),)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_message_to_conversation(prospect_email: str, subject: str, sender: str, message: str):
    db = next(get_db())
    normalized_subject = normalize_subject(subject)
    # Query now uses both email and subject
    conversation = db.query(Conversation).filter_by(prospect_email=prospect_email, subject=normalized_subject).first()

    if not conversation:
        # Be explicit on creation to ensure the field is never NULL
        conversation = Conversation(prospect_email=prospect_email, subject=normalized_subject, conversation_history="[]")
        db.add(conversation)

    # FIX: Handle the case where the history might be None or an empty string from the DB
    history_str = conversation.conversation_history
    history = json.loads(history_str) if history_str else []
    history.append({"sender": sender, "message": message})
    conversation.conversation_history = json.dumps(history, indent=2)

    db.commit()
    db.refresh(conversation)

def get_conversation_history(prospect_email: str, subject: str) -> str:
    db = next(get_db())
    # Normalize the subject to ensure consistent querying
    normalized_subject = normalize_subject(subject)
    # Query now uses both email and subject
    conversation = db.query(Conversation).filter_by(prospect_email=prospect_email, subject=normalized_subject).first()
    
    # FIX: Handle cases where conversation doesn't exist or its history is None/empty
    if conversation and conversation.conversation_history:
        # We can return the raw string here, as it's already a JSON string
        return conversation
        
    return "[]"

def mark_research_performed(prospect_email: str, subject: str):
    """Sets the research_performed flag to True for a conversation."""
    db = next(get_db())
    normalized_subject = normalize_subject(subject)
    conversation = db.query(Conversation).filter_by(prospect_email=prospect_email, subject=normalized_subject).first()

    if conversation:
        conversation.research_performed = True
        db.commit()
        db.refresh(conversation)
        return True
    
    return False