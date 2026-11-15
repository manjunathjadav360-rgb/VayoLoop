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
        self.assertIn('initial_sidebar_state="auto"', source)
        self.assertIn("html { font-size: 118%; }", source)
        self.assertIn("[role=\"combobox\"]", source)
        self.assertIn("parse_aware_india_datetime", source)
        self.assertIn('"Data quality": "Needs review" if item.get("validation_issue") else "Validated"', source)
        self.assertIn("excluded from numerical trend analysis", source)
        self.assertIn("--vl-paper:#BC8F8F", source)
        self.assertIn("--vl-silver:#C0C0C0", source)
        self.assertIn(".stButton > button", source)
        self.assertIn(".stDownloadButton > button", source)
        self.assertIn("#voiceEnable", source)
        self.assertNotIn("stButton > button[kind=\"primary\"] { background:var(--vl-green)", source)
        theme = (APP_PATH.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn('backgroundColor = "#BC8F8F"', theme)
        self.assertIn('primaryColor = "#C0C0C0"', theme)
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
