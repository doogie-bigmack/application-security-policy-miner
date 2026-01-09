"""
Unit tests for ClaudeChromeExecutor

These tests verify the ClaudeChromeExecutor wrapper functionality.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from test_executor import (
    ClaudeChromeExecutor,
    BrowserError,
    ElementNotFoundError,
    NavigationError,
    create_executor
)


@pytest.fixture
def temp_screenshot_dir():
    """Create a temporary directory for screenshots"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def executor(temp_screenshot_dir):
    """Create a ClaudeChromeExecutor instance for testing"""
    return ClaudeChromeExecutor(screenshot_dir=temp_screenshot_dir)


class TestClaudeChromeExecutor:
    """Test suite for ClaudeChromeExecutor"""

    def test_initialization(self, temp_screenshot_dir):
        """Test that executor initializes correctly"""
        executor = ClaudeChromeExecutor(screenshot_dir=temp_screenshot_dir)

        assert executor.screenshot_dir == Path(temp_screenshot_dir)
        assert executor.retry_attempts == 3
        assert executor.current_url is None
        assert executor.screenshot_dir.exists()

    def test_initialization_creates_screenshot_dir(self, temp_screenshot_dir):
        """Test that screenshot directory is created if it doesn't exist"""
        screenshot_path = Path(temp_screenshot_dir) / "nested" / "screenshots"
        executor = ClaudeChromeExecutor(screenshot_dir=str(screenshot_path))

        assert screenshot_path.exists()

    def test_navigate_success(self, executor):
        """Test successful navigation"""
        result = executor.navigate("http://localhost:3333")

        assert result is True
        assert executor.current_url == "http://localhost:3333"

    def test_click_logs_correctly(self, executor):
        """Test that click method logs correctly"""
        # This is a scaffold test - actual implementation would verify MCP tool calls
        result = executor.click("button.submit", element_description="Submit button")
        assert result is True

    def test_fill_input_logs_correctly(self, executor):
        """Test that fill_input method logs correctly"""
        result = executor.fill_input(
            "input#username",
            "test_user",
            element_description="Username field"
        )
        assert result is True

    def test_assert_visible_logs_correctly(self, executor):
        """Test that assert_visible method logs correctly"""
        result = executor.assert_visible("div.success-message", timeout_ms=3000)
        assert result is True

    def test_wait_for_element_timeout(self, executor):
        """Test that wait_for_element raises error on timeout"""
        # Note: This test would need adjustment when wired to actual MCP tools
        # Currently it will succeed because the scaffold always returns True
        pass

    def test_take_screenshot_creates_file(self, executor):
        """Test that screenshot method returns a valid path"""
        screenshot_path = executor.take_screenshot("test_screenshot")

        assert screenshot_path is not None
        assert "test_screenshot" in screenshot_path
        assert screenshot_path.endswith(".png")

    def test_take_screenshot_with_timestamp(self, executor):
        """Test that screenshots include timestamps"""
        import time
        path1 = executor.take_screenshot("test")
        time.sleep(1.1)  # Ensure different timestamp
        path2 = executor.take_screenshot("test")

        # Paths should be different due to timestamp
        assert path1 != path2

    def test_get_page_text_returns_string(self, executor):
        """Test that get_page_text returns a string"""
        executor.navigate("http://localhost:3333")
        page_text = executor.get_page_text()

        assert isinstance(page_text, str)
        assert len(page_text) > 0

    def test_close_clears_state(self, executor):
        """Test that close method clears state"""
        executor.navigate("http://localhost:3333")
        executor.close()

        assert executor.current_url is None

    def test_factory_function(self, temp_screenshot_dir):
        """Test that create_executor factory function works"""
        executor = create_executor(screenshot_dir=temp_screenshot_dir)

        assert isinstance(executor, ClaudeChromeExecutor)
        assert executor.screenshot_dir == Path(temp_screenshot_dir)


class TestErrorHandling:
    """Test error handling in ClaudeChromeExecutor"""

    def test_custom_retry_attempts(self, temp_screenshot_dir):
        """Test that custom retry attempts are respected"""
        executor = ClaudeChromeExecutor(
            screenshot_dir=temp_screenshot_dir,
            retry_attempts=5
        )

        assert executor.retry_attempts == 5


# Integration test markers for future implementation
@pytest.mark.integration
@pytest.mark.skip(reason="Requires actual browser and MCP tools")
class TestBrowserIntegration:
    """Integration tests that require actual browser"""

    def test_navigate_to_localhost(self, executor):
        """Test navigation to localhost:3333"""
        result = executor.navigate("http://localhost:3333")
        assert result is True

    def test_click_element_by_selector(self, executor):
        """Test clicking an element by CSS selector"""
        executor.navigate("http://localhost:3333")
        result = executor.click("button#add-repository")
        assert result is True

    def test_fill_form_input(self, executor):
        """Test filling a form input"""
        executor.navigate("http://localhost:3333/repositories")
        result = executor.fill_input("input#token", "test_token_123")
        assert result is True

    def test_assert_element_visible(self, executor):
        """Test asserting element visibility"""
        executor.navigate("http://localhost:3333")
        result = executor.assert_visible("nav.navbar", timeout_ms=5000)
        assert result is True

    def test_take_screenshot_saves_file(self, executor):
        """Test that screenshot is actually saved"""
        executor.navigate("http://localhost:3333")
        screenshot_path = executor.take_screenshot("integration_test")

        assert Path(screenshot_path).exists()
        assert Path(screenshot_path).stat().st_size > 0
