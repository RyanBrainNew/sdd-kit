import re
import unittest
from pathlib import Path

from sdd.scripts import sdd as engine


KIT_ROOT = Path(__file__).resolve().parents[1]
DOC = KIT_ROOT / "docs" / "STANDARD-CONFORMANCE.md"
ENTRIES = [f"P{index}" for index in range(6)] + [
    f"G{index}" for index in range(6)
]
STATUSES = {"已自动", "已人工", "部分实现", "未实现"}


def mapping_rows():
    text = DOC.read_text(encoding="utf-8")
    header = None
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = engine.split_table_row(stripped)
        if "条目" in cells and "状态" in cells:
            header = cells
            continue
        if header is None or not cells:
            continue
        if re.fullmatch(r"[PG][0-5]", cells[0]):
            rows.append(cells)
    return header, rows


class StandardConformanceTests(unittest.TestCase):
    def test_all_entries_present(self):
        self.assertTrue(DOC.is_file(), "缺少 docs/STANDARD-CONFORMANCE.md")
        header, rows = mapping_rows()
        self.assertIsNotNone(header)
        for column in ("条目", "官方阶段/Gate", "实现方式", "证据位置", "缺口", "状态"):
            self.assertIn(column, header)
        found = [row[0] for row in rows]
        self.assertEqual(sorted(found), sorted(ENTRIES))
        self.assertEqual(len(found), len(set(found)))
        for row in rows:
            self.assertEqual(len(row), 6)
            for value in row[2:6]:
                self.assertTrue(value.strip(), f"{row[0]} 有空字段")
            index = int(row[0][1:])
            stage = engine.GATE_STAGES[f"G{index}"]
            self.assertIn(stage[0], row[1])
            self.assertIn(stage[1], row[1])

    def test_status_values_allowed(self):
        _, rows = mapping_rows()
        self.assertEqual(len(rows), 12)
        for row in rows:
            self.assertIn(row[5], STATUSES, f"{row[0]} 状态非法")

    def test_check_ids_exist(self):
        text = DOC.read_text(encoding="utf-8")
        ids = set(re.findall(r"\bG[0-5]-\d{2}\b", text))
        unknown = sorted(ids - set(engine.CHECK_REGISTRY_BY_ID))
        self.assertEqual(unknown, [], f"未知检查 ID：{unknown}")


if __name__ == "__main__":
    unittest.main()
