import os
import platform
import subprocess
from threading import Lock, Thread

from PIL import Image

from weather_frame import logger

DEBUG_MODE = os.environ.get("DEBUG_MODE", "0") == "1" or platform.system() == "Windows"

if not DEBUG_MODE:
    from inky.auto import auto

class DisplayService:
    def __init__(self):
        self.screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        os.makedirs(self.screenshots_dir, exist_ok=True)
        self.screenshot_path = os.path.join(self.screenshots_dir, 'screenshot.png')

        # An e-ink write takes seconds and is not reentrant; concurrent screenshot
        # + show() calls (overlapping refreshes) would corrupt the panel. Hold this
        # for the whole screenshot->display cycle and skip if already running.
        self._update_lock = Lock()
        
        # Snapshot the debug state per-instance so tests can flip it (and the
        # injected `inky` mock) without re-importing the module.
        self.debug_mode = DEBUG_MODE

        # Initialize inky display if not in debug mode
        if not self.debug_mode:
            # ask_user=False: no TTY under systemd, an interactive prompt would hang boot.
            self.inky = auto(ask_user=False, verbose=True)
        else:
            self.inky = None
    
    @staticmethod
    def _crop_image(image, target_width, target_height):
        """Crop image from right and bottom to match target dimensions.
        
        Args:
            image: PIL Image object
            target_width: Desired width
            target_height: Desired height
            
        Returns:
            Cropped PIL Image
        """
        img_width, img_height = image.size
        
        width_to_use = min(img_width, target_width)
        height_to_use = min(img_height, target_height)
        
        if width_to_use != img_width or height_to_use != img_height:
            return image.crop((0, 0, width_to_use, height_to_use))
        return image

    @staticmethod
    def _resize_image(image, target_width, target_height):
        """Resize image to fill target dimensions if it's too small in any dimension.
        Maintains aspect ratio and centers the content.
        
        Args:
            image: PIL Image object
            target_width: Desired width
            target_height: Desired height
            
        Returns:
            Resized PIL Image
        """
        img_width, img_height = image.size
        
        if img_width < target_width or img_height < target_height:
            resized_image = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 255))
            
            scale_width = target_width / img_width if img_width < target_width else 1
            scale_height = target_height / img_height if img_height < target_height else 1
            
            scale = min(scale_width, scale_height)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            resized_content = image.resize((new_width, new_height), Image.LANCZOS)
            
            paste_x = (target_width - new_width) // 2
            paste_y = (target_height - new_height) // 2
            resized_image.paste(resized_content, (paste_x, paste_y))
            
            return resized_image
        return image
    
    def display_screenshot(self, filepath, saturation=0.0):
        """Display a screenshot on the Inky Impression display.

        Args:
            filepath: Path to the screenshot file.
            saturation: Color saturation level (default: 0.0)
        """
        if self.debug_mode or not self.inky:
            logger.info(f"Debug mode: Would display {filepath} on e-ink display")
            return
        
        image = Image.open(filepath)
        
        # Get display dimensions
        target_width, target_height = self.inky.resolution
        
        # Process the image
        image = self._crop_image(image, target_width, target_height)
        image = self._resize_image(image, target_width, target_height)

        try:
            self.inky.set_image(image, saturation=saturation)
        except TypeError:
            self.inky.set_image(image)

        self.inky.show()
    
    def take_screenshot_and_update_display(self):
        """Take a screenshot of the weather dashboard using headless Chromium."""
        # Non-blocking: if a previous update is still running, skip this one rather
        # than queueing a second concurrent Chromium + e-ink write.
        if not self._update_lock.acquire(blocking=False):
            logger.info("Display update already in progress, skipping")
            return False
        try:
            url = "http://localhost:8080"
            
            if platform.system() == "Windows":
                cmd = [
                    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                    '--headless=new',
                    '--disable-gpu',
                    '--window-size=820,520',
                    '--force-device-scale-factor=2',
                    '--no-sandbox',
                    '--disable-software-rasterizer',
                    '--hide-scrollbars',
                    '--virtual-time-budget=1000',
                    '--screenshot=' + self.screenshot_path,
                    url
                ]
            else:
                cmd = [
                    'chromium-browser',
                    '--headless',
                    '--disable-gpu',
                    '--window-size=800,520',
                    '--no-sandbox',
                    '--disable-software-rasterizer',
                    "--disable-dev-shm-usage",
                    "--disable-features=UseDBus",
                    '--hide-scrollbars',
                    '--virtual-time-budget=1000',
                    '--screenshot=' + self.screenshot_path,
                    url
                ]
                
            subprocess.run(cmd, check=True)
            
            # Display the screenshot on e-ink display
            self.display_screenshot(self.screenshot_path)
            
            if DEBUG_MODE:
                logger.info(f"Debug mode: Screenshot saved to {self.screenshot_path}")

            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
        finally:
            self._update_lock.release()

    def update_display_async(self):
        """Update display in a separate thread"""
        Thread(target=self.take_screenshot_and_update_display).start()