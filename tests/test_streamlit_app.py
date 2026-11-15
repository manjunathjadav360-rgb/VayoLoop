import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
SECTIONS = [
    "Home",
    "Medicines",
    "Health journal",
    "Appointments",
    "Family circle",
    "Emergency centre",
    "Connected living",
    "Local support",
    "Care Passport",
]


class StreamlitPageSmokeTests(unittest.TestCase):
    def test_every_main_section_renders_without_exception(self):
        for section in SECTIONS:
            with self.subTest(section=section):
                app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
                self.assertFalse(app.exception, f"Home page failed: {app.exception}")
                app.sidebar.radio[0].set_value(section).run()
                self.assertFalse(app.exception, f"{section} failed: {app.exception}")


if __name__ == "__main__":
    unittest.main()
