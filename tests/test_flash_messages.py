"""
Tests for the custom flash message system.
"""

import unittest
from unittest.mock import patch
import flask
from webapp.flash_messages import (
    flash_message,
    get_flash_messages,
    get_all_flash_messages,
    clear_flash_messages,
    has_flash_messages,
    FLASH_MESSAGES_KEY,
)


class TestFlashMessages(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.app = flask.Flask(__name__)
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()

    def test_flash_message_basic(self):
        """Test basic flash message functionality."""
        with self.app.test_request_context("/test"):
            # Flash a message
            request_id = flash_message("Test message", "positive")

            # Check that request_id is returned
            self.assertIsInstance(request_id, str)
            self.assertTrue(len(request_id) > 0)

            # Check that message is stored in session
            self.assertIn(FLASH_MESSAGES_KEY, flask.session)
            self.assertIn(request_id, flask.session[FLASH_MESSAGES_KEY])

            # Check message content
            msg_data = flask.session[FLASH_MESSAGES_KEY][request_id]
            self.assertEqual(msg_data["message"], "Test message")
            self.assertEqual(msg_data["category"], "positive")
            self.assertFalse(msg_data["consumed"])

    def test_get_flash_messages(self):
        """Test retrieving flash messages by request ID."""
        with self.app.test_request_context("/test"):
            # Flash a message
            request_id = flash_message("Test message", "positive")

            # Get messages
            messages = get_flash_messages(request_id)
            self.assertEqual(messages, ["Test message"])

            # Check that message is marked as consumed
            msg_data = flask.session[FLASH_MESSAGES_KEY][request_id]
            self.assertTrue(msg_data["consumed"])

    def test_get_flash_messages_with_categories(self):
        """Test retrieving flash messages with categories."""
        with self.app.test_request_context("/test"):
            # Flash a message
            request_id = flash_message("Test message", "positive")

            # Get messages with categories
            messages = get_flash_messages(request_id, with_categories=True)
            self.assertEqual(messages, [("positive", "Test message")])

    def test_get_flash_messages_with_category_filter(self):
        """Test retrieving flash messages with category filter."""
        with self.app.test_request_context("/test"):
            # Flash messages with different categories
            request_id1 = flash_message("Positive message", "positive")
            request_id2 = flash_message("Negative message", "negative")

            # Get only positive messages
            messages1 = get_flash_messages(
                request_id1, category_filter=["positive"]
            )
            self.assertEqual(messages1, ["Positive message"])

            # Get only negative messages
            messages2 = get_flash_messages(
                request_id2, category_filter=["negative"]
            )
            self.assertEqual(messages2, ["Negative message"])

            # Try to get positive message with negative filter
            messages3 = get_flash_messages(
                request_id1, category_filter=["negative"]
            )
            self.assertEqual(messages3, [])

    def test_get_all_flash_messages(self):
        """Test retrieving all flash messages."""
        with self.app.test_request_context("/test"):
            # Flash multiple messages
            flash_message("Message 1", "positive")
            flash_message("Message 2", "negative")

            # Get all messages
            messages = get_all_flash_messages()
            self.assertEqual(len(messages), 2)
            self.assertIn("Message 1", messages)
            self.assertIn("Message 2", messages)

    def test_clear_flash_messages(self):
        """Test clearing flash messages."""
        with self.app.test_request_context("/test"):
            # Flash a message
            request_id = flash_message("Test message", "positive")

            # Check message exists
            self.assertTrue(has_flash_messages(request_id))

            # Clear specific message
            clear_flash_messages(request_id)

            # Check message is gone
            self.assertFalse(has_flash_messages(request_id))

    def test_clear_all_flash_messages(self):
        """Test clearing all flash messages."""
        with self.app.test_request_context("/test"):
            # Flash multiple messages
            flash_message("Message 1", "positive")
            flash_message("Message 2", "negative")

            # Check messages exist
            self.assertTrue(has_flash_messages())

            # Clear all messages
            clear_flash_messages()

            # Check all messages are gone
            self.assertFalse(has_flash_messages())

    def test_has_flash_messages(self):
        """Test checking for flash messages."""
        with self.app.test_request_context("/test"):
            # Initially no messages
            self.assertFalse(has_flash_messages())

            # Flash a message
            request_id = flash_message("Test message", "positive")

            # Check message exists
            self.assertTrue(has_flash_messages())
            self.assertTrue(has_flash_messages(request_id))

            # Consume message
            get_flash_messages(request_id)

            # Check message is consumed
            self.assertFalse(has_flash_messages(request_id))

    def test_message_cleanup(self):
        """Test that old messages are cleaned up."""
        with self.app.test_request_context("/test"):
            with patch("webapp.flash_messages.time.time") as mock_time:
                # Set initial time
                mock_time.return_value = 1000

                # Flash a message
                request_id = flash_message("Old message", "positive")

                # Move time forward beyond MAX_MESSAGE_AGE
                mock_time.return_value = 1000 + 400  # 400 seconds later

                # Flash another message (this should trigger cleanup)
                flash_message("New message", "positive")

                # Old message should be gone
                self.assertFalse(has_flash_messages(request_id))

    def test_no_request_context(self):
        """Test behavior when there's no request context."""
        # Test without request context
        request_id = flash_message("Test message", "positive")
        self.assertEqual(request_id, "")

        messages = get_flash_messages("test_id")
        self.assertEqual(messages, [])

        all_messages = get_all_flash_messages()
        self.assertEqual(all_messages, [])

        self.assertFalse(has_flash_messages())


if __name__ == "__main__":
    unittest.main()
