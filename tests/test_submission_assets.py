import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SubmissionAssetsTests(unittest.TestCase):
    def test_modelscope_runtime_files_exist(self):
        self.assertTrue((ROOT / "app.py").is_file())
        self.assertTrue((ROOT / "requirements.txt").is_file())
        self.assertTrue((ROOT / "README.md").is_file())

    def test_readme_contains_required_disclosure_and_demo_path(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("OPC Gate 空间匹配与申请助手", readme)
        self.assertIn("ModelScope", readme)
        self.assertIn("活动期间首次发布", readme)
        self.assertIn("既有 OPC Gate", readme)
        self.assertIn("128", readme)
        self.assertIn("申请入口", readme)
        self.assertIn("不代表入驻资格", readme)

    def test_submission_copy_uses_space_matching_positioning(self):
        files = [
            "01-报名文案.md", "02-作品提交资料.md", "03-研习社创作手记.md",
            "04-社媒参赛心得.md", "05-演示脚本.md",
        ]
        combined = "\n".join((ROOT / "submission" / filename).read_text(encoding="utf-8") for filename in files)
        self.assertIn("空间匹配", combined)
        self.assertIn("申请", combined)
        self.assertNotIn("**OPC Gate 政策内容运营助手**", combined)

    def test_submission_pack_has_all_deliverables(self):
        required = [
            "01-报名文案.md",
            "02-作品提交资料.md",
            "03-研习社创作手记.md",
            "04-社媒参赛心得.md",
            "05-演示脚本.md",
            "06-提交检查清单.md",
        ]
        for filename in required:
            self.assertTrue((ROOT / "submission" / filename).is_file(), filename)


if __name__ == "__main__":
    unittest.main()
