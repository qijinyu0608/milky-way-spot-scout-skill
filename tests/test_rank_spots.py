import json
import subprocess
import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPT = SKILL_DIR / "scripts" / "rank_spots.py"
FIXTURE = TESTS_DIR / "fixtures" / "sample_candidates.json"


def run_rank_spots(*extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), *extra_args],
        check=True,
        capture_output=True,
        text=True,
    )


class RankSpotsRenderTests(unittest.TestCase):
    def test_markdown_output_matches_skill_contract(self) -> None:
        result = run_rank_spots("--format", "markdown", "--top", "3")
        output = result.stdout

        self.assertIn("| 排名 | 地点 | 总分 | 天气分 | 云量 | 湿度 | 能见度 | 光污染 | 观测日期/窗口 | 一句话判断 |", output)
        self.assertIn("## 1. Example Ridge", output)
        self.assertIn("### 观测窗口", output)
        self.assertIn("### 天气明细", output)
        self.assertIn("### 暗空明细", output)
        self.assertIn("### 月亮明细", output)
        self.assertIn("### 银河几何明细", output)
        self.assertIn("### 交通与安全明细", output)
        self.assertIn("### 简短结论", output)
        self.assertIn("## 数据新鲜度说明", output)
        self.assertIn("- smoke_risk：低", output)
        self.assertIn("- haze_risk：中", output)
        self.assertIn("- city_glow_direction：northwest", output)
        self.assertIn("- city_glow_risk：中", output)
        self.assertIn("- parking_risk：高", output)
        self.assertIn("- walking_risk：高", output)
        self.assertIn("来源：未记录", output)
        self.assertIn("；说明：基于该来源推算", output)
        self.assertNotIn("| Metric | Score | Inputs | Sources |", output)
        self.assertNotIn("## Data Freshness", output)

        first_card = output.split("## 2. Desert Overlook", 1)[0]
        self.assertLess(first_card.index("### 观测窗口"), first_card.index("### 天气明细"))
        self.assertLess(first_card.index("### 天气明细"), first_card.index("### 暗空明细"))
        self.assertLess(first_card.index("### 暗空明细"), first_card.index("### 月亮明细"))
        self.assertLess(first_card.index("### 月亮明细"), first_card.index("### 银河几何明细"))
        self.assertLess(first_card.index("### 银河几何明细"), first_card.index("### 交通与安全明细"))
        self.assertGreaterEqual(output.count("来源："), 18)

    def test_both_format_preserves_structured_payload(self) -> None:
        result = run_rank_spots("--format", "both", "--top", "3")
        payload = json.loads(result.stdout)

        self.assertEqual(set(payload.keys()), {"markdown", "structured"})
        self.assertIn("### 天气明细", payload["markdown"])
        self.assertIn("数据新鲜度说明", payload["markdown"])

        structured = payload["structured"]
        self.assertIn("weights", structured)
        self.assertIn("preferences", structured)
        self.assertIn("ranked_candidates", structured)
        self.assertEqual(len(structured["ranked_candidates"]), 3)

        first = structured["ranked_candidates"][0]
        for key in [
            "name",
            "region",
            "rank",
            "total_score",
            "component_scores",
            "moon_window_status",
            "weather_requirement_status",
            "confidence_status",
            "missing_fields",
            "summary",
            "score_breakdown",
            "evidence",
            "candidate",
        ]:
            self.assertIn(key, first)

    def test_json_format_shape_is_unchanged(self) -> None:
        result = run_rank_spots("--format", "json", "--top", "2")
        payload = json.loads(result.stdout)

        self.assertEqual(set(payload.keys()), {"weights", "preferences", "ranked_candidates"})
        self.assertEqual(len(payload["ranked_candidates"]), 2)
        self.assertEqual(payload["ranked_candidates"][0]["candidate"]["name"], "Example Ridge")
        self.assertAlmostEqual(payload["ranked_candidates"][0]["forecast_confidence_normalized"], 82.0)
        self.assertAlmostEqual(payload["ranked_candidates"][1]["forecast_confidence_normalized"], 68.0)


if __name__ == "__main__":
    unittest.main()
