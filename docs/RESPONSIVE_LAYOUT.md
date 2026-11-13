# Compact Windows layout correction

## Root cause

The original dashboard used a fixed three-column `QGridLayout`. Qt summed the minimum widths of its three metric cards, two 14-pixel gaps and the page's 56 pixels of horizontal margins. Plain `QLabel` word wrapping still treated an unbroken value such as “Unavailable” as an indivisible minimum-width word. A `QLayout.SetMinimumSize` scroll-page constraint propagated that combined width into the body. Disabling the horizontal scrollbar did not make the content responsive; it could leave content wider than the viewport.

There were additional sums in the dashboard summary and non-wrapping footer. Similar rigid horizontal rows existed in monitor/benchmark cards, optimization filters, action badges/buttons, the header, profile controls and settings. Native push buttons also default to a non-shrinking minimum sizing policy; wrapping text alone is insufficient unless button geometry and height-for-width are updated together.

The reported Windows failure was a 1086-pixel minimum inside a 688-pixel viewport. Windows-specific contributor sizes were not measured in this Linux workspace. Local instrumentation confirmed the same structural defect: the old dashboard requested 654 pixels normally and 876 pixels with larger font metrics, still inside a 688-pixel viewport. The old metric grid alone requested 820 pixels in the latter case, before page margins.

## Actual layout changes

- `ResponsiveGrid` rearranges cards into 1..N columns using available logical width, current font metrics and content. It reports and allocates the full height of every row. Dashboard metrics/summary, monitor cards and benchmark metrics use it.
- `FlowLayout` wraps complete controls and calculates each item's actual height-for-width. Filters, action footers, guided workflows, profiles, the header and footer no longer require one unbroken horizontal row.
- `WrappingLabel` uses the same Qt text document for measurement and painting, with word-boundary/anywhere wrapping. Long hardware identifiers, editions and paths are not elided or changed. Selection and copying preserve plain text, including Unicode paths.
- Command/navigation buttons retain native button behavior and accessible names, with wrapping captions, appropriate shrinking/growing policies and height-for-width. Sidebar branding and collapse controls can also wrap; navigation remains vertically scrollable. Caption contrast follows the actual button state.
- Window minimum size remains **920×480**. No essential controls are removed, hidden based on width, or made unavailable to satisfy a width assertion. Optimization/backup/session behavior is unchanged.

## Regression and build checks

The original `test_navigation_and_compact_layout` remains unchanged. `tests/test_responsive_layout.py` additionally checks every page with populated cards and larger fonts, actual body/viewport width, absence of page horizontal overflow, allocated text heights, 3→2→1→3 card reflow, visible/non-overlapping cards/controls, sidebar accessibility, and exact plain-text clipboard contents.

Windows CI runs these layout regressions in **separate Python processes** with `QT_SCALE_FACTOR=1`, `1.25`, `1.5`, and `2`, before packaging. The step restores its environment afterwards so the extracted Windows ZIP smoke test still uses the normal Windows Qt platform. `ApexxTweaks.exe`, `ApexxTweaks-windows-x64.zip`, artifact names and packaging checks remain intact.

Actual local results are recorded in [VALIDATION.md](VALIDATION.md). Offscreen Qt scaling checks on Linux do not replace a native Windows CI run or manual Windows display-scaling verification.
