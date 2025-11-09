"""
UUIDv7 utilities using the uuid6 library for generating time-ordered UUIDs
"""
import time
import uuid
from typing import Union
from uuid6 import uuid7


def generate_uuidv7() -> str:
    """
    Generate a UUIDv7 (time-ordered UUID) as a string using uuid6 library.
    
    Returns:
        String representation of UUIDv7
    """
    return str(uuid7())


def generate_uuidv7_obj() -> uuid.UUID:
    """
    Generate a UUIDv7 as a UUID object.
    
    Returns:
        UUID object representing UUIDv7
    """
    return uuid7()


def is_uuidv7(uuid_str: Union[str, uuid.UUID]) -> bool:
    """
    Check if a UUID string or object is UUIDv7.
    
    Args:
        uuid_str: UUID string or UUID object to check
        
    Returns:
        True if UUID is version 7, False otherwise
    """
    try:
        if isinstance(uuid_str, str):
            uuid_obj = uuid.UUID(uuid_str)
        else:
            uuid_obj = uuid_str
        
        return uuid_obj.version == 7
    except (ValueError, AttributeError):
        return False


def extract_timestamp_from_uuidv7(uuid_str: Union[str, uuid.UUID]) -> int:
    """
    Extract timestamp (milliseconds since epoch) from UUIDv7.
    
    Args:
        uuid_str: UUIDv7 string or UUID object
        
    Returns:
        Timestamp in milliseconds since Unix epoch
        
    Raises:
        ValueError: If UUID is not version 7
    """
    try:
        if isinstance(uuid_str, str):
            uuid_obj = uuid.UUID(uuid_str)
        else:
            uuid_obj = uuid_str
            
        if uuid_obj.version != 7:
            raise ValueError(f"UUID {uuid_obj} is not version 7")
            
        # Extract first 48 bits as timestamp
        uuid_bytes = uuid_obj.bytes
        timestamp_bytes = uuid_bytes[:6]
        timestamp_ms = int.from_bytes(timestamp_bytes, byteorder='big')
        
        return timestamp_ms
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid UUIDv7: {e}")


# Convenience function for backward compatibility
def uuidv7() -> str:
    """Generate UUIDv7 string (alias for generate_uuidv7)"""
    return generate_uuidv7()
