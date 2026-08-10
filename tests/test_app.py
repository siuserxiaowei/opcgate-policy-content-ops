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

        fake_gradio.themes.Soft.assert_called_once_with(primary_hue="emerald", secondary_hue="slate")
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

    def test_recommendations_change_with_city_industry_stage_and_services(self):
        data = app.load_data(ROOT / "data")
        profile = {
            "city": "广州",
            "industry": "AI / 大模型",
            "stage": "已有 Demo",
            "services": ["低成本工位", "算力 / Token", "融资路演"],
            "description": "正在做企业智能体产品，需要试用客户和算力。",
        }
        results = app.recommend_spaces(profile, data["communities"], data["policies"], limit=8)
        self.assertGreaterEqual(len(results), 3)
        self.assertTrue(all(item["city"] == "广州" for item in results))
        self.assertEqual(results[0]["name"], "琶洲模方 SOPC加速器")
        self.assertIn("AI", " ".join(results[0]["match_reasons"]))
        self.assertTrue(any("算力" in reason or "Token" in reason for reason in results[0]["match_reasons"]))

        cross_border = app.recommend_spaces({
            **profile,
            "industry": "跨境 / 出海",
            "services": ["跨境服务", "注册政务"],
        }, data["communities"], data["policies"], limit=8)
        self.assertEqual(cross_border[0]["name"], "南沙国际OPC生态社区")
        self.assertNotEqual([item["name"] for item in results[:3]], [item["name"] for item in cross_border[:3]])

    def test_recommendation_has_explainable_evidence_and_application_state(self):
        data = app.load_data(ROOT / "data")
        results = app.recommend_spaces({
            "city": "广州", "industry": "AI / 大模型", "stage": "已有 Demo",
            "services": ["低成本工位", "算力 / Token"], "description": "智能体产品",
        }, data["communities"], data["policies"])
        required = {
            "name", "score", "match_reasons", "address", "operator", "features",
            "evidence_status", "source_url", "application_status", "application_url", "boundary",
        }
        self.assertTrue(required.issubset(results[0]))
        self.assertGreaterEqual(len(results[0]["match_reasons"]), 2)
        self.assertNotIn("获批概率", results[0]["boundary"])
        self.assertIn("推荐", results[0]["boundary"])

    def test_missing_source_never_creates_fake_application_link(self):
        community = {
            "id": "missing-source", "name": "待核验空间", "city": "广州", "province": "广东",
            "district": "天河", "address": "待核验", "operator": "", "track": "AI",
            "features": ["创业工位"], "verified": False, "policy_ids": [],
        }
        result = app.recommend_spaces({
            "city": "广州", "industry": "AI / 大模型", "stage": "只有想法",
            "services": ["低成本工位"], "description": "",
        }, [community], [])[0]
        self.assertEqual(result["source_url"], "")
        self.assertEqual(result["application_url"], "")
        self.assertEqual(result["application_status"], "联系运营方 / 核验入口")
        self.assertEqual(result["evidence_status"], "信息待核验")

    def test_only_explicit_online_entry_is_exposed_as_application_url(self):
        data = app.load_data(ROOT / "data")
        results = app.recommend_spaces({
            "city": "广州", "industry": "跨境 / 出海", "stage": "已注册企业",
            "services": ["注册政务", "跨境服务"], "description": "跨境 AI 产品",
        }, data["communities"], data["policies"], limit=12)
        nansha = next(item for item in results if item["name"] == "南沙国际OPC生态社区")
        self.assertEqual(nansha["application_status"], "公开线上入口")
        self.assertEqual(nansha["application_url"], "https://scjgj.gz.gov.cn/ywt/")
        pazhou = next(item for item in app.recommend_spaces({
            "city": "广州", "industry": "AI / 大模型", "stage": "已有 Demo",
            "services": ["算力 / Token"], "description": "AI 产品",
        }, data["communities"], data["policies"], limit=12) if item["name"] == "琶洲模方 SOPC加速器")
        self.assertEqual(pazhou["application_url"], "")
        self.assertEqual(pazhou["application_status"], "准备申请 / 联系运营方")

    def test_compare_two_or_three_spaces_and_rejects_other_counts(self):
        data = app.load_data(ROOT / "data")
        results = app.recommend_spaces({
            "city": "广州", "industry": "AI / 大模型", "stage": "已有 Demo",
            "services": ["低成本工位", "算力 / Token"], "description": "AI 产品",
        }, data["communities"], data["policies"], limit=5)
        comparison = app.compare_spaces([item["id"] for item in results[:3]], results)
        self.assertEqual(len(comparison), 3)
        self.assertTrue(all("推荐依据" in row and "下一步" in row for row in comparison))
        with self.assertRaisesRegex(ValueError, "2–3"):
            app.compare_spaces([results[0]["id"]], results)
        with self.assertRaisesRegex(ValueError, "2–3"):
            app.compare_spaces([item["id"] for item in results[:4]], results)

    def test_application_checklist_changes_by_stage(self):
        idea = app.build_application_checklist("只有想法")
        registered = app.build_application_checklist("已注册企业")
        self.assertIn("一页项目说明", idea)
        self.assertIn("身份证明", idea)
        self.assertIn("营业执照", registered)
        self.assertIn("财务或纳税", registered)
        self.assertNotEqual(idea, registered)

    def test_empty_filters_and_no_results_have_safe_behavior(self):
        data = app.load_data(ROOT / "data")
        with self.assertRaisesRegex(ValueError, "城市"):
            app.recommend_spaces({"city": "", "industry": "AI / 大模型", "stage": "已有 Demo", "services": []}, data["communities"], data["policies"])
        self.assertEqual(app.recommend_spaces({
            "city": "不存在的城市", "industry": "AI / 大模型", "stage": "已有 Demo", "services": []
        }, data["communities"], data["policies"]), [])

    def test_ui_helpers_render_result_empty_compare_and_checklist_states(self):
        data = app.load_data(ROOT / "data")
        profile = {
            "city": "广州", "industry": "跨境 / 出海", "stage": "已注册企业",
            "services": ["注册政务", "跨境服务"], "description": "跨境 AI 产品",
        }
        results = app.recommend_spaces(profile, data["communities"], data["policies"], limit=12)
        cards = app._result_cards(results)
        self.assertIn("南沙国际OPC生态社区", cards)
        self.assertIn("打开公开入口", cards)
        self.assertIn("准备申请 / 联系运营方", cards)
        self.assertIn("没有找到同城载体", app._result_cards([]))

        summary = app._search_summary(profile, results, data)
        self.assertIn("同城候选", summary)
        self.assertIn("跨境 / 出海", summary)
        empty = app._search_summary({**profile, "city": "不存在的城市"}, [], data)
        self.assertIn("暂无同城结果", empty)

        ui_output = app.ui_recommend(
            "广州", "AI / 大模型", "已有 Demo",
            ["低成本工位", "算力 / Token", "融资路演"], "企业智能体产品",
        )
        self.assertEqual(len(ui_output), 6)
        state = ui_output[3]
        self.assertEqual(state["results"][0]["name"], "琶洲模方 SOPC加速器")
        selected = [item["id"] for item in state["results"][:2]]
        comparison = app.ui_compare(selected, state)
        self.assertIn("横向比较", comparison)
        self.assertIn("琶洲模方", comparison)
        self.assertIn("请选择 2–3", app.ui_compare(selected[:1], state))

    def test_invalid_or_private_source_url_is_removed(self):
        self.assertEqual(app.safe_public_url("javascript:alert(1)"), "")
        self.assertEqual(app.safe_public_url("http://127.0.0.1/private"), "")
        self.assertEqual(app.safe_public_url("https://example.com/post"), "https://example.com/post")


if __name__ == "__main__":
    unittest.main()
