import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
SECTIONS = [
    "Home",
    "Medicines",
    "Prescription library",
    "Health journal",
    "Appointments",
    "Family circle",
    "Emergency centre",
    "Connected living",
    "Local support",
    "Care Passport",
]


class StreamlitPageSmokeTests(unittest.TestCase):
    def test_source_uses_current_streamlit_embedding_and_width_apis(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertIn("st.iframe(", source)
        self.assertNotIn("components.v1.html", source)
        self.assertNotIn("use_container_width", source)

    def test_every_main_section_renders_without_exception(self):
        for section in SECTIONS:
            with self.subTest(section=section):
                app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
                self.assertFalse(app.exception, f"Home page failed: {app.exception}")
                app.sidebar.radio[0].set_value(section).run()
                self.assertFalse(app.exception, f"{section} failed: {app.exception}")


if __name__ == "__main__":
    unittest.main()
