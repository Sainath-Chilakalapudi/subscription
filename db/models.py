from sqlalchemy import Index, Integer, Column, Boolean, BigInteger, String, Date, DateTime, ForeignKey, UniqueConstraint , func
from sqlalchemy.orm import relationship
from db.connection import Base  # Assuming you have a Base defined in your connection module

class Channel(Base):
    __tablename__ = 'channels'

    channel_id = Column(BigInteger, primary_key=True)
    channel_name = Column(String, nullable=False)
    invite_link = Column(String, nullable=True)
    is_channel =Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationship with subscriptions
    subscriptions = relationship("Subscription", back_populates="channel")
    # Relationship with pending requests
    pending_requests = relationship("PendingRequest", back_populates="channel")

class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    fullname = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationship with subscriptions
    subscriptions = relationship("Subscription", back_populates="user")
    # Relationship with pending requests
    pending_requests = relationship("PendingRequest", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', fullname='{self.fullname}')>"
    
    def to_dict(self):
      """
      Converts the User object to a dictionary, including related subscriptions.
      """
      user_dict = {
          'user_id': self.user_id,
          'username': self.username,
          'fullname': self.fullname,
          'created_at': self.created_at.isoformat() if self.created_at else None,  # Convert datetime to ISO string
          'subscriptions': [sub.to_dict() for sub in self.subscriptions] if self.subscriptions else []  #Convert Subscriptions to a list of Dictionaries
      }
      return user_dict


class Subscription(Base):
    __tablename__ = 'subscriptions'

    subscription_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete="CASCADE"))
    channel_id = Column(BigInteger, ForeignKey('channels.channel_id', ondelete="CASCADE"))
    expiry_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    channel = relationship("Channel", back_populates="subscriptions")

    # Index
    __table_args__ = (
        Index('idx_user_channel', 'user_id', 'channel_id', unique=True),  # Composite index for user+channel
        Index('idx_expiry_date', 'expiry_date'),
    )

    def __repr__(self):
        return (f"<Subscription(subscription_id={self.subscription_id}, "
                f"user_id='{self.user_id}', channel_id='{self.channel_id}', "
                f"expiry_date='{self.expiry_date}', created_at='{self.created_at}')>")

    def to_dict(self):
        return {
            "subscription_id": self.subscription_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class VerificationCode(Base):
    __tablename__ = 'verification_codes'

    code = Column(String, primary_key=True)
    admin_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Index
    __table_args__ = (
        Index('idx_code_expires', 'code', 'expires_at'),  # Composite index for code and expiry
    )


class PendingRequest(Base):
    __tablename__ = 'pending_requests'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    channel_id = Column(BigInteger, ForeignKey('channels.channel_id'), nullable=False)
    admin_id = Column(BigInteger, nullable=False)
    duration = Column(Integer, nullable=True)

    # Create relationships with User and Channel
    user = relationship('User', back_populates='pending_requests')
    channel = relationship('Channel', back_populates='pending_requests')

    # Index on channel_id to speed up lookups
    __table_args__ = (
        Index('ix_pending_requests_channel_id', 'channel_id'),
        UniqueConstraint('user_id', 'channel_id', name='uq_user_channel'),
    )