import importlib.util
import os
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("contest_app", ROOT / "app.py")
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class ContestAppTests(unittest.TestCase):
    def test_launch_demo_passes_gradio_6_options(self):
        demo = MagicMock()
        fake_gradio = MagicMock()
        fake_theme = object()
        fake_gradio.themes.Soft.return_value = fake_theme

        with patch.dict("sys.modules", {"gradio": fake_gradio}), patch.object(app, "build_demo", return_value=demo):
            app.launch_demo()

        fake_gradio.themes.Soft.assert_called_once_with(primary_hue="blue", secondary_hue="teal")
        demo.launch.assert_called_once_with(theme=fake_theme, css=app.CSS)

    def test_mobile_css_constrains_gradio_root_and_tables(self):
        self.assertIn("width:100% !important", app.CSS)
        self.assertIn("min-width:0 !important", app.CSS)
        self.assertIn(".gradio-container .table-wrap", app.CSS)
        self.assertIn("overflow-x:auto !important", app.CSS)

    def setUp(self):
        self.topic = {
            "title": "AI 智能体创业者如何寻找落地政策",
            "text": "园区内容运营需要把公开话题与人工智能、一人公司、算力和创业空间政策关联起来。",
            "source_url": "https://example.com/public-topic",
            "mode": "手动输入公开内容",
            "observed_at": "2026-08-10",
        }

    def test_loads_full_opcgate_data_scope(self):
        data = app.load_data(ROOT / "data")
        self.assertEqual(len(data["policies"]), 125)
        self.assertEqual(len(data["cities"]), 42)
        self.assertEqual(len(data["communities"]), 128)
        self.assertEqual(data["snapshot"], "2026-05-22")

    def test_report_is_for_policy_content_operations(self):
        data = app.load_data(ROOT / "data")
        report = app.analyze_topic(self.topic, data)
        self.assertEqual(report["product_name"], "OPC Gate 政策内容运营助手")
        self.assertGreaterEqual(len(report["matches"]), 1)
        self.assertIn("事实", report["draft"])
        self.assertIn("推断", report["draft"])
        self.assertIn("待核验", report["draft"])
        self.assertIn("人工核验", report["draft"])
        self.assertNotIn("#微博VibeLab#", report["draft"])
        self.assertNotIn("#VibeSocial#", report["draft"])

    def test_report_preserves_evidence_and_no_eligibility_promise(self):
        data = app.load_data(ROOT / "data")
        report = app.analyze_topic(self.topic, data)
        self.assertTrue(any(item["source_url"].startswith("https://") for item in report["matches"]))
        self.assertTrue(all("资格" in item["boundary"] for item in report["matches"]))
        self.assertNotRegex(report["draft"], r"保证|必得|必拿|100%|已获批")

    def test_publish_gate_rejects_unsafe_model_copy(self):
        data = app.load_data(ROOT / "data")
        report = app.analyze_topic(self.topic, data)
        unsafe = "官方推荐，保证符合申报条件，最高可得 100 万元。"
        scan = app.scan_draft(unsafe, report)
        self.assertFalse(scan["passed"])
        codes = {item["code"] for item in scan["violations"]}
        self.assertIn("guaranteed_claim", codes)
        self.assertIn("qualification_claim", codes)
        self.assertIn("missing_layers", codes)

    def test_modelscope_ai_falls_back_without_token(self):
        data = app.load_data(ROOT / "data")
        report = app.analyze_topic(self.topic, data)
        old = os.environ.pop("MODELSCOPE_ACCESS_TOKEN", None)
        try:
            result = app.rewrite_with_modelscope(report)
        finally:
            if old is not None:
                os.environ["MODELSCOPE_ACCESS_TOKEN"] = old
        self.assertFalse(result["used"])
        self.assertEqual(result["draft"], report["draft"])
        self.assertIn("未配置", result["reason"])

    def test_invalid_or_private_source_url_is_removed(self):
        self.assertEqual(app.safe_public_url("javascript:alert(1)"), "")
        self.assertEqual(app.safe_public_url("http://127.0.0.1/private"), "")
        self.assertEqual(app.safe_public_url("https://example.com/post"), "https://example.com/post")


if __name__ == "__main__":
    unittest.main()
