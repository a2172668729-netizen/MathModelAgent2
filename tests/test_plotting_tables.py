from __future__ import annotations

from pathlib import Path

import pandas as pd

from mmagent.plotting import bar_chart, heatmap_chart, line_chart, scatter_chart
from mmagent.tables import dataframe_to_latex_table, latex_escape


def _assert_png_svg(paths: list[Path]) -> None:
    assert {path.suffix for path in paths} == {".png", ".svg"}
    assert all(path.is_file() and path.stat().st_size > 100 for path in paths)


def test_line_scatter_bar_and_heatmap_generation(tmp_path: Path) -> None:
    _assert_png_svg(line_chart([0, 1, 2], [1, 2, 4], tmp_path / "line"))
    _assert_png_svg(scatter_chart([0, 1, 2], [1, 2, 4], tmp_path / "scatter"))
    _assert_png_svg(bar_chart(["甲", "乙"], [1, 2], tmp_path / "bar"))
    _assert_png_svg(heatmap_chart([[1, 2], [3, 4]], tmp_path / "heatmap"))


def test_latex_table_booktabs_escape_precision_and_missing_values(tmp_path: Path) -> None:
    frame = pd.DataFrame({"名称_含&符号": ["A&B", "50%"], "数值": [1.23456789, float("nan")]})
    path = dataframe_to_latex_table(
        frame,
        tmp_path / "table.tex",
        caption="参数_表&格",
        label="tab:special",
        digits=4,
    )

    text = path.read_text(encoding="utf-8")
    assert "\\toprule" in text and "\\bottomrule" in text
    assert "A\\&B" in text and "50\\%" in text
    assert "名称\\_含\\&符号" in text
    assert "1.2346" in text and "--" in text
    assert latex_escape(r"a_b%") == r"a\_b\%"
