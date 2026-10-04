// Draws the dashboard charts from the JSON the view puts in #chart-data.
// Colours come from CSS variables in app.css, so they are defined in one place.
(function () {
  "use strict";

  const dataTag = document.getElementById("chart-data");
  if (!dataTag || typeof Chart === "undefined") return;

  const css = getComputedStyle(document.querySelector(".viz-root") || document.body);
  const token = (name) => css.getPropertyValue(name).trim();
  const palette = [token("--series-1"), token("--series-2")]; // fixed order, never cycled
  const grid = token("--viz-grid");
  const muted = token("--viz-muted");

  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
  Chart.defaults.color = muted;

  // Recessive axes: hairline grid, muted labels, whole numbers only.
  const axis = (showGrid) => ({
    grid: { display: showGrid, color: grid },
    border: { color: grid },
    ticks: { color: muted, precision: 0 },
    beginAtZero: true,
  });

  function barChart(spec, canvas) {
    const horizontal = spec.horizontal;
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: spec.labels,
        datasets: [{
          label: spec.series[0].name,
          data: spec.series[0].values,
          backgroundColor: palette[0],
          borderRadius: 4,          // rounds the data end only (baseline end is skipped)
          maxBarThickness: 18,      // thin marks
          categoryPercentage: 0.8,  // leaves a gap between bars
        }],
      },
      options: {
        indexAxis: horizontal ? "y" : "x",
        maintainAspectRatio: false,
        plugins: { legend: { display: false } }, // one series: the title names it
        scales: horizontal
          ? { x: axis(true), y: axis(false) }
          : { x: axis(false), y: axis(true) },
      },
    });
  }

  function lineChart(spec, canvas) {
    return new Chart(canvas, {
      type: "line",
      data: {
        labels: spec.labels,
        datasets: spec.series.map((s, i) => ({
          label: s.name,
          data: s.values,
          borderColor: palette[i],
          backgroundColor: palette[i],
          borderWidth: 2,
          pointRadius: 4,           // 8px markers
          pointHoverRadius: 6,
          pointBorderColor: token("--viz-surface"), // surface ring where markers overlap
          pointBorderWidth: 2,
          tension: 0,
        })),
      },
      options: {
        maintainAspectRatio: false,
        // Hover anywhere in a month column to see both values together.
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "top", align: "start", labels: { usePointStyle: true, boxWidth: 8 } } },
        scales: { x: axis(false), y: axis(true) },
      },
    });
  }

  JSON.parse(dataTag.textContent).forEach((spec) => {
    const canvas = document.getElementById("chart-" + spec.id);
    if (!canvas) return;
    (spec.type === "line" ? lineChart : barChart)(spec, canvas);
  });
})();
