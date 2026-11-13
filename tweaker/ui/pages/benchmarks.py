"""Product page. Controls delegate to the controller, never Windows writes."""

from PySide6.QtWidgets import (
    QLineEdit,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from ..widgets import (
    Card,
    MetricCard,
    ResponsiveGrid,
    Chart,
    Histogram,
    ComparisonChart,
    label,
    button,
)


from .common import Page, details, confirm, page_header, row, control


class Benchmarks(Page):
    def __init__(self, window):
        super().__init__(window)
        self.comparison = None
        self._seen_import = None
        page_header(
            self.box,
            "Benchmarks",
            "Measure the difference. Keep the conditions matched. Let repeat runs tell the story.",
        )
        context = Card()
        context.box.addWidget(label("Your experiment", "heading"))
        self.context = QLineEdit()
        self.context.setAccessibleName("Matched experiment context")
        self.context.setPlaceholderText(
            "Scene / hardware / driver / resolution / rendering mode / frame cap"
        )
        context.box.addWidget(self.context)
        context.box.addLayout(
            row(
                control(
                    self,
                    "Import before CSV",
                    lambda: self.import_capture("Before"),
                    True,
                ),
                control(self, "Import after CSV", lambda: self.import_capture("After")),
                control(self, "Compare runs", self.compare_runs),
                control(self, "Export results", self.export_results),
                control(self, "New experiment", self.new_experiment),
            )
        )
        context.box.addWidget(
            label(
                "Import at least three independent runs per condition. File times must be milliseconds; mixed process/swapchain streams and duplicate files are rejected.",
                "muted",
            )
        )
        self.box.addWidget(context)
        self.metrics_grid = metrics = ResponsiveGrid(max_columns=4, preferred_width=185)
        self.metrics = []
        for name in ["Average FPS", "1% low FPS", "0.1% low FPS", "p99 · ms"]:
            card = MetricCard(name, "—", "Select an imported run")
            self.metrics.append(card)
            metrics.addWidget(card)
        self.box.addLayout(metrics)
        plot = Card()
        plot.box.addWidget(label("Frame-time distribution", "heading"))
        self.histogram = Histogram()
        plot.box.addWidget(self.histogram)
        plot.box.addWidget(
            label(
                "Lower frame times are better. Every imported frame contributes; stutters are not trimmed.",
                "muted",
            )
        )
        self.box.addWidget(plot)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Condition / capture", "Average FPS", "1% low", "0.1% low", "Duration"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(180)
        self.table.itemSelectionChanged.connect(self.selected_run)
        self.empty_runs = label(
            "No captures imported yet. Add a before capture to start a measured baseline.",
            "muted",
        )
        self.box.addWidget(self.empty_runs)
        self.box.addWidget(self.table)
        self.trace_card = Card()
        self.trace_card.box.addWidget(
            label("Frame-time trace · bucket peaks", "heading")
        )
        self.trace = Chart("Frame-time trace", "ms", limit=None)
        self.trace_card.box.addWidget(self.trace)
        self.trace_note = label(
            "Import a new capture to see the preserved peak in each frame bucket.",
            "muted",
        )
        self.trace_card.box.addWidget(self.trace_note)
        self.box.addWidget(self.trace_card)
        self.result = Card()
        self.result.box.addWidget(label("Before / after analysis", "heading"))
        self.result_text = label(
            "No comparison yet. Repeated matched captures help distinguish improvements from ordinary run-to-run variation.",
            "muted",
        )
        self.result.box.addWidget(self.result_text)
        self.comparison_table = QTableWidget(0, 5)
        self.comparison_table.setHorizontalHeaderLabels(
            ["Metric", "Before", "After", "Change", "95% delta CI"]
        )
        self.comparison_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.comparison_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.comparison_table.setMinimumHeight(175)
        self.comparison_table.hide()
        self.result.box.addWidget(self.comparison_table)
        self.comparison_chart = ComparisonChart()
        self.comparison_chart.hide()
        self.result.box.addWidget(self.comparison_chart)
        self.result.box.addLayout(
            row(
                button(
                    "Calculation details",
                    lambda: details(
                        window,
                        "Benchmark methodology",
                        "Average FPS = 1000 / mean frame time. Lows = 1000 / mean of slowest ceil(1% or 0.1%) frames. p99 uses nearest rank. Independent-run bootstrap intervals are exploratory, especially with few runs. They do not prove causality or measure input latency.\n\nMatch capture semantics, scene, warm-up, duration, cap and thermal conditions.",
                    ),
                )
            )
        )
        self.box.addWidget(self.result)
        self.box.addStretch()

    def import_capture(self, condition):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Import " + condition.lower() + " capture",
            "",
            "Frame-time CSV (*.csv)",
        )
        if path:
            self.c.import_run(path, condition, self.context.text())

    def compare_runs(self):
        def done(report):
            self.comparison = report
            self.show_comparison()

        self.c.compare(done)

    def show_comparison(self):
        if not self.comparison:
            return
        report = self.comparison
        self.comparison_table.setRowCount(4)
        self.comparison_table.show()
        self.comparison_chart.set_metrics(report["metrics"])
        self.comparison_chart.show()
        for i, (key, m) in enumerate(report["metrics"].items()):
            interval = m["bootstrap_95_percentile_interval"]
            unit = "ms" if key == "p99_ms" else "FPS"
            values = [
                key.replace("_", " "),
                f"{m['before_mean']:.2f} {unit}",
                f"{m['after_mean']:.2f} {unit}",
                f"{m['percent']:+.1f}%",
                f"{interval[0]:+.2f} to {interval[1]:+.2f} {unit}",
            ]
            for j, v in enumerate(values):
                self.comparison_table.setItem(i, j, QTableWidgetItem(v))
        self.result_text.setText(
            f"{report['runs_before']} before · {report['runs_after']} after · {report['context']}\n"
            + "\n".join(report["warnings"])
            + "\nExploratory run-level bootstrap. No causality or input-latency claim. p99: lower is better; FPS metrics: higher is better."
        )

    def export_results(self):
        path, _ = QFileDialog.getSaveFileName(
            self.window, "Export benchmark results", "", "JSON (*.json)"
        )
        if path:
            try:
                self.c.export(path)
                self.window.toast(
                    "Results exported. Review paths and history before sharing."
                )
            except Exception as error:
                self.window.show_error(str(error))

    def new_experiment(self):
        if confirm(
            self.window,
            "Archive experiment",
            "Archive the current captures and start an empty experiment? Action backups and journals are preserved.",
        ):
            try:
                if self.c.new_experiment():
                    self.context.clear()
                    self.comparison = None
                    self.comparison_table.hide()
                    self.comparison_chart.hide()
                    self.histogram.set_values([])
                    self.trace.set_values([])
                    self.result_text.setText(
                        "New experiment ready. Previous runs were archived."
                    )
                    for card in self.metrics:
                        card.set("—", "Import or select a run")
            except Exception as error:
                self.window.show_error(str(error))

    def selected_run(self):
        index = self.table.currentRow()
        if not 0 <= index < len(getattr(self, "run_rows", [])):
            return
        r = self.run_rows[index]
        for card, key in zip(
            self.metrics, ["average_fps", "low_1", "low_01", "p99_ms"]
        ):
            value = r.get(key)
            card.set(
                f"{value:.2f}" if value is not None else "Unavailable",
                r.get("source", "Legacy capture"),
            )
        self.histogram.set_values(r.get("histogram", []))
        self.trace.set_values(r.get("frame_trace_ms", []))
        self.trace_note.setText(
            f"Each point is the maximum of up to {r.get('trace_bucket_frames', 1)} consecutive frames; peaks are preserved. Not a raw frame-by-frame trace."
            if r.get("frame_trace_ms")
            else "This legacy capture contains no trace metadata. Its existing FPS metrics and histogram are preserved."
        )

    def refresh(self):
        previous = self.table.currentRow()
        self.table.blockSignals(True)
        self.run_rows = [
            r for condition in ("Before", "After") for r in self.c.runs[condition]
        ]
        self.table.setRowCount(len(self.run_rows))
        self.table.setVisible(bool(self.run_rows))
        self.empty_runs.setVisible(not self.run_rows)
        self.trace_card.setVisible(bool(self.run_rows))
        i = 0
        for condition in ("Before", "After"):
            for r in self.c.runs[condition]:
                values = (
                    [condition + " · " + r.get("source", "Legacy capture")]
                    + [
                        f"{r[k]:.2f}" if r.get(k) is not None else "Unavailable"
                        for k in ("average_fps", "low_1", "low_01")
                    ]
                    + [
                        f"{r['duration_s']:.1f} s"
                        if r.get("duration_s")
                        else "Unavailable"
                    ]
                )
                for j, v in enumerate(values):
                    self.table.setItem(i, j, QTableWidgetItem(v))
                i += 1
        if self.c.last_import and self.c.last_import != self._seen_import:
            previous = next(
                (
                    i
                    for i, r in enumerate(self.run_rows)
                    if r.get("source_sha256") == self.c.last_import
                ),
                previous,
            )
            self._seen_import = self.c.last_import
        if self.run_rows:
            self.table.selectRow(
                previous
                if 0 <= previous < len(self.run_rows)
                else len(self.run_rows) - 1
            )
        self.table.blockSignals(False)
        if self.run_rows:
            self.selected_run()
