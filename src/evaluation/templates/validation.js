const report = JSON.parse(document.getElementById("report-data").textContent);
const labels = {
  pts: "Points", reb: "Rebounds", ast: "Assists", stl: "Steals", blk: "Blocks",
  tov: "Turnovers", fgm: "Field goals made", fga: "Field goals attempted",
  fg3m: "Three-pointers made", ftm: "Free throws made", fta: "Free throws attempted",
  fantasy_points: "Fantasy points"
};
const controls = Object.fromEntries(
  ["statistic", "player", "start", "end"].map(id => [id, document.getElementById(id)])
);
const playerIds = new Map();
const numberFormat = new Intl.NumberFormat(undefined, {maximumFractionDigits: 3});
const plotConfig = {responsive: true, displaylogo: false};

function chartLayout(xTitle, yTitle) {
  return {
    margin: {l: 60, r: 20, t: 20, b: 60},
    xaxis: {title: {text: xTitle}, automargin: true},
    yaxis: {title: {text: yTitle}, automargin: true},
    legend: {orientation: "h", y: 1.15},
    font: {family: "system-ui, sans-serif", color: "#182b40"},
    paper_bgcolor: "white", plot_bgcolor: "white"
  };
}

function selectedRows() {
  const playerLabel = controls.player.value.trim();
  return report.rows.filter(row => (
    (!playerLabel || row.player_id === playerIds.get(playerLabel)) &&
    (!controls.start.value || row.game_date >= controls.start.value) &&
    (!controls.end.value || row.game_date <= controls.end.value)
  ));
}

function dailyResults(rows, statistic) {
  const days = new Map();
  for (const row of rows) {
    const day = days.get(row.game_date) || {count: 0, actual: 0, predicted: 0, absolute: 0, error: 0};
    const error = row.predicted[statistic] - row.actual[statistic];
    day.count++;
    day.actual += row.actual[statistic];
    day.predicted += row.predicted[statistic];
    day.absolute += Math.abs(error);
    day.error += error;
    days.set(row.game_date, day);
  }
  return [...days].sort(([first], [second]) => first.localeCompare(second)).map(([date, day]) => ({
    date, count: day.count, actual: day.actual / day.count, predicted: day.predicted / day.count,
    mae: day.absolute / day.count, bias: day.error / day.count
  }));
}

async function render() {
  const rows = selectedRows();
  const statistic = controls.statistic.value;
  const label = labels[statistic];
  document.getElementById("count").textContent = numberFormat.format(rows.length);
  document.getElementById("charts").hidden = rows.length === 0;
  document.getElementById("empty").hidden = rows.length !== 0;
  document.getElementById("selection").textContent = `${label} · ${controls.player.value || "All players"} · ${controls.start.value} through ${controls.end.value}`;
  if (!rows.length) {
    for (const id of ["mae", "rmse", "bias"]) document.getElementById(id).textContent = "—";
    return;
  }
  const actual = rows.map(row => row.actual[statistic]);
  const predicted = rows.map(row => row.predicted[statistic]);
  const errors = rows.map((row, index) => predicted[index] - actual[index]);
  const mean = values => values.reduce((total, value) => total + value, 0) / values.length;
  document.getElementById("mae").textContent = numberFormat.format(mean(errors.map(Math.abs)));
  document.getElementById("rmse").textContent = numberFormat.format(Math.sqrt(mean(errors.map(error => error * error))));
  document.getElementById("bias").textContent = numberFormat.format(mean(errors));
  const low = Math.min(...actual, ...predicted);
  const high = Math.max(...actual, ...predicted);
  const bounds = low === high ? [low - 1, high + 1] : [low, high];
  // All eligible appearances are shown; no sampling hides large misses.
  const scatterLayout = chartLayout(`Actual ${label.toLowerCase()}`, `Predicted ${label.toLowerCase()}`);
  scatterLayout.xaxis.range = bounds;
  scatterLayout.yaxis.range = bounds;
  const scatter = Plotly.react("scatter", [
    {type: "scattergl", mode: "markers", x: actual, y: predicted, name: "Appearances",
      customdata: rows.map(row => [row.player_name, row.game_date, row.game_id]),
      hovertemplate: "%{customdata[0]} · %{customdata[1]}<br>Game %{customdata[2]}<br>Actual %{x:.2f}<br>Predicted %{y:.2f}<extra></extra>",
      marker: {size: 5, opacity: .3, color: "#2877b8"}},
    {type: "scatter", mode: "lines", x: bounds, y: bounds, name: "Perfect prediction",
      line: {color: "#d35d31", dash: "dash"}, hoverinfo: "skip"}
  ], scatterLayout, plotConfig);
  const histogramLayout = chartLayout("Prediction error", "Appearances");
  histogramLayout.shapes = [{type: "line", x0: 0, x1: 0, y0: 0, y1: 1, yref: "paper",
    line: {color: "#d35d31", dash: "dash"}}];
  const histogram = Plotly.react("histogram", [
    {type: "histogram", x: errors, nbinsx: 50, marker: {color: "#2877b8"}, name: "Errors"}
  ], histogramLayout, plotConfig);
  const daily = dailyResults(rows, statistic);
  const dates = daily.map(day => day.date);
  const line = (key, name, color) => ({
    type: "scatter", mode: "lines+markers", x: dates, y: daily.map(day => day[key]),
    name, line: {color}, marker: {size: 4}, customdata: daily.map(day => day.count),
    hovertemplate: "%{x}<br>%{y:.3f}<br>%{customdata} appearances<extra>%{fullData.name}</extra>"
  });
  document.getElementById("timeline-help").textContent = controls.player.value
    ? "Actual and predicted values for each selected appearance. Look for streaks of overprediction or underprediction."
    : "Daily average actual and predicted values across selected appearances. Individual errors can cancel; use MAE to assess accuracy.";
  const timeline = Plotly.react("timeline", [
    line("actual", "Actual", "#2877b8"), line("predicted", "Predicted", "#d35d31")
  ], chartLayout("Game date", label), plotConfig);
  const errorLayout = chartLayout("Game date", `${label} error`);
  errorLayout.shapes = [{type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0,
    line: {color: "#b5c3d3", dash: "dash"}}];
  const errorChart = Plotly.react("errors", [
    line("mae", "MAE", "#2877b8"), line("bias", "Mean signed error", "#d35d31")
  ], errorLayout, plotConfig);
  await Promise.all([scatter, histogram, timeline, errorChart]);
}

for (const statistic of report.statistics) {
  controls.statistic.add(new Option(labels[statistic], statistic));
}
controls.statistic.value = "fantasy_points";
const players = new Map(report.rows.map(row => [row.player_id, row.player_name]));
for (const [id, name] of [...players].sort((first, second) => first[1].localeCompare(second[1]))) {
  const label = `${name} (${id})`;
  playerIds.set(label, id);
  document.getElementById("players").append(new Option(label, label));
}
const dates = report.rows.map(row => row.game_date).sort();
function resetDates() {
  controls.start.value = dates[0];
  controls.end.value = dates[dates.length - 1];
}
resetDates();
const season = report.summary.seasons[report.summary.validation_season];
document.getElementById("scope").textContent = `Validation ${report.summary.validation_season}: ${season.eligible_rows.toLocaleString()} eligible appearances; ${season.warmup_excluded_rows.toLocaleString()} excluded by history requirements. Test ${report.summary.reserved_test_season} is reserved.`;
for (const control of Object.values(controls)) control.addEventListener("change", render);
document.getElementById("reset").addEventListener("click", () => {
  controls.statistic.value = "fantasy_points";
  controls.player.value = "";
  resetDates();
  render();
});
render();
