from sqlalchemy import BigInteger, Column, Integer, String, Text

from database import Base


class LedLog(Base):
    __tablename__ = "LedLoglari"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    led = Column(String)
    sequence = Column(BigInteger)
    device_timestamp = Column(BigInteger)
    nonce = Column(String)
    server_received_at = Column(BigInteger)
    message = Column(Text, nullable=True)
    encryption_version = Column(Integer, nullable=False, server_default="0")
    md5_checksum = Column(String(32), nullable=True)


class DeviceCommand(Base):
    __tablename__ = "CihazEmirleri"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    komut = Column(String)
    durum = Column(String, default="bekliyor")
    olusturulma_zamani = Column(BigInteger)
    message = Column(Text, nullable=True)
    encryption_version = Column(Integer, nullable=False, server_default="0")
    md5_checksum = Column(String(32), nullable=True)
