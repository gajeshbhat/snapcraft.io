"""
Custom flash message system to prevent cross-tab flash message issues.

This module provides a replacement for Flask's built-in flash message system
that associates messages with specific requests/pages rather than just the
session, preventing flash messages from appearing on unrelated pages when
users have multiple tabs open.
"""

import uuid
import time
from typing import List, Optional, Dict, Any
import flask


# Flash message storage key in session
FLASH_MESSAGES_KEY = "_custom_flash_messages"
# Maximum age for flash messages in seconds (5 minutes)
MAX_MESSAGE_AGE = 60
# Maximum number of messages to store per session
MAX_MESSAGES_PER_SESSION = 25


def _get_request_id() -> str:
    """
    Generate a unique identifier for the current request.
    This combines the request path with a UUID to create a unique identifier
    that can be used to associate flash messages with specific pages.
    """
    if not flask.has_request_context():
        return str(uuid.uuid4())

    # Use the request path as part of the identifier
    path = flask.request.path
    # Add a UUID to make it unique for this specific request
    request_uuid = str(uuid.uuid4())
    return f"{path}:{request_uuid}"


def _cleanup_old_messages(messages: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove old flash messages to prevent memory leaks.
    """
    current_time = time.time()
    cleaned_messages = {}

    for msg_id, msg_data in messages.items():
        if current_time - msg_data.get("timestamp", 0) < MAX_MESSAGE_AGE:
            cleaned_messages[msg_id] = msg_data

    return cleaned_messages


def flash_message(
    message: str, category: str = "message", request_id: Optional[str] = None
) -> str:
    """
    Flash a message to be displayed on a specific page.

    Args:
        message: The message to be flashed
        category: The category for the message (e.g., 'positive', 'negative',
                 'information')
        request_id: Optional request ID to associate the message with. If not
                   provided, a new one will be generated.

    Returns:
        The request ID that can be used to retrieve the message
    """
    if not flask.has_request_context():
        return ""

    if request_id is None:
        request_id = _get_request_id()

    # Get existing messages from session
    messages = flask.session.get(FLASH_MESSAGES_KEY, {})

    # Clean up old messages
    messages = _cleanup_old_messages(messages)

    # Limit the number of messages to prevent memory issues
    if len(messages) >= MAX_MESSAGES_PER_SESSION:
        # Remove the oldest message
        oldest_key = min(
            messages.keys(), key=lambda k: messages[k].get("timestamp", 0)
        )
        del messages[oldest_key]

    # Add the new message
    messages[request_id] = {
        "message": message,
        "category": category,
        "timestamp": time.time(),
        "consumed": False,
    }

    flask.session[FLASH_MESSAGES_KEY] = messages
    return request_id


def get_flash_messages(
    request_id: str,
    with_categories: bool = False,
    category_filter: Optional[List[str]] = None,
) -> List[Any]:
    """
    Get flash messages for a specific request ID.

    Args:
        request_id: The request ID to get messages for
        with_categories: Whether to return tuples of (category, message)
        category_filter: Optional list of categories to filter by

    Returns:
        List of messages or (category, message) tuples
    """
    if not flask.has_request_context():
        return []

    messages = flask.session.get(FLASH_MESSAGES_KEY, {})

    if request_id not in messages:
        return []

    msg_data = messages[request_id]

    # Mark as consumed
    msg_data["consumed"] = True
    flask.session[FLASH_MESSAGES_KEY] = messages

    # Filter by category if specified
    if category_filter and msg_data["category"] not in category_filter:
        return []

    if with_categories:
        return [(msg_data["category"], msg_data["message"])]
    else:
        return [msg_data["message"]]


def get_all_flash_messages(
    with_categories: bool = False, category_filter: Optional[List[str]] = None
) -> List[Any]:
    """
    Get all unconsumed flash messages for the current session.
    This is a fallback for compatibility with existing templates.

    Args:
        with_categories: Whether to return tuples of (category, message)
        category_filter: Optional list of categories to filter by

    Returns:
        List of messages or (category, message) tuples
    """
    if not flask.has_request_context():
        return []

    messages = flask.session.get(FLASH_MESSAGES_KEY, {})
    result = []

    # Clean up old messages
    messages = _cleanup_old_messages(messages)

    for msg_id, msg_data in messages.items():
        if msg_data.get("consumed", False):
            continue

        # Filter by category if specified
        if category_filter and msg_data["category"] not in category_filter:
            continue

        if with_categories:
            result.append((msg_data["category"], msg_data["message"]))
        else:
            result.append(msg_data["message"])

        # Mark as consumed
        msg_data["consumed"] = True

    flask.session[FLASH_MESSAGES_KEY] = messages
    return result


def clear_flash_messages(request_id: Optional[str] = None) -> None:
    """
    Clear flash messages. If request_id is provided, only clear messages for
    that request. Otherwise, clear all messages.

    Args:
        request_id: Optional request ID to clear messages for
    """
    if not flask.has_request_context():
        return

    if request_id is None:
        # Clear all messages
        flask.session[FLASH_MESSAGES_KEY] = {}
    else:
        # Clear specific message
        messages = flask.session.get(FLASH_MESSAGES_KEY, {})
        if request_id in messages:
            del messages[request_id]
            flask.session[FLASH_MESSAGES_KEY] = messages


def has_flash_messages(request_id: Optional[str] = None) -> bool:
    """
    Check if there are any flash messages.

    Args:
        request_id: Optional request ID to check for. If not provided, checks
                   for any messages.

    Returns:
        True if there are messages, False otherwise
    """
    if not flask.has_request_context():
        return False

    messages = flask.session.get(FLASH_MESSAGES_KEY, {})

    if request_id is not None:
        return request_id in messages and not messages[request_id].get(
            "consumed", False
        )

    # Check for any unconsumed messages
    for msg_data in messages.values():
        if not msg_data.get("consumed", False):
            return True

    return False
