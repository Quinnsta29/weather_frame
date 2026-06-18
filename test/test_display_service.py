from unittest.mock import MagicMock

import pytest
from PIL import Image

from weather_frame.display_service import DisplayService


@pytest.fixture
def service():
    """A DisplayService (debug mode is forced via conftest, so no hardware)."""
    return DisplayService()


class TestCropImage:
    def test_crops_oversized_from_top_left(self):
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        result = DisplayService._crop_image(img, 50, 40)
        assert result.size == (50, 40)

    def test_small_image_returned_unchanged(self):
        img = Image.new("RGB", (30, 30), (0, 0, 0))
        result = DisplayService._crop_image(img, 50, 50)
        assert result is img


class TestResizeImage:
    def test_undersized_scaled_onto_target_canvas(self):
        img = Image.new("RGB", (40, 40), (0, 0, 0))
        result = DisplayService._resize_image(img, 100, 80)
        assert result.size == (100, 80)

    def test_large_enough_returned_unchanged(self):
        img = Image.new("RGB", (200, 200), (0, 0, 0))
        result = DisplayService._resize_image(img, 100, 80)
        assert result is img


class TestDisplayScreenshot:
    def test_debug_mode_skips_hardware(self, service):
        service.debug_mode = True
        service.inky = MagicMock()

        service.display_screenshot("anything.png")

        service.inky.set_image.assert_not_called()
        service.inky.show.assert_not_called()

    def test_hardware_path_sets_and_shows(self, service, tmp_path):
        service.debug_mode = False
        service.inky = MagicMock(resolution=(800, 480))
        png = tmp_path / "shot.png"
        Image.new("RGB", (800, 480), (255, 255, 255)).save(png)

        service.display_screenshot(str(png), saturation=0.5)

        service.inky.set_image.assert_called_once()
        service.inky.show.assert_called_once()

    def test_set_image_typeerror_fallback(self, service, tmp_path):
        service.debug_mode = False
        # First call (with saturation kwarg) raises TypeError, retry succeeds.
        service.inky = MagicMock(resolution=(800, 480))
        service.inky.set_image.side_effect = [TypeError("no saturation"), None]
        png = tmp_path / "shot.png"
        Image.new("RGB", (800, 480), (255, 255, 255)).save(png)

        service.display_screenshot(str(png), saturation=0.5)

        assert service.inky.set_image.call_count == 2
        service.inky.show.assert_called_once()


class TestTakeScreenshot:
    def test_debug_invokes_display_without_chromium(self, service, monkeypatch):
        fake_run = MagicMock()
        monkeypatch.setattr("weather_frame.display_service.subprocess.run", fake_run)
        # Stub platform.system too: mocking subprocess.run otherwise breaks
        # platform's own internal shell-out on the next platform.system() call.
        monkeypatch.setattr("weather_frame.display_service.platform.system", lambda: "Linux")
        service.display_screenshot = MagicMock()
        service.debug_mode = True

        result = service.take_screenshot_and_update_display()

        assert result is True
        fake_run.assert_called_once()
        service.display_screenshot.assert_called_once_with(service.screenshot_path)

    def test_subprocess_failure_returns_false(self, service, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("chromium missing")
        monkeypatch.setattr("weather_frame.display_service.subprocess.run", boom)
        monkeypatch.setattr("weather_frame.display_service.platform.system", lambda: "Linux")

        result = service.take_screenshot_and_update_display()

        assert result is False
