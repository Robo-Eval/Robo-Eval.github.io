(() => {
  const scopeSelect = document.getElementById("leaderboard-scope-select");
  const tableHead = document.getElementById("leaderboard-head");
  const tableBody = document.getElementById("leaderboard-body");
  const hint = document.getElementById("leaderboard-hint");

  if (!scopeSelect || !tableHead || !tableBody) {
    return;
  }

  let schema = [];
  let byTask = {};
  let globalRows = [];
  let sortState = { key: "success", order: "desc" };
  const EXCLUDED_METHODS = new Set(["human", "humans"]);

  function formatNumber(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return "-";
    if (Math.abs(v) >= 100) return v.toFixed(1);
    if (Math.abs(v) >= 10) return v.toFixed(2);
    return v.toFixed(3);
  }

  function formatMetricCell(metricValue) {
    if (!metricValue || metricValue.mean === null || metricValue.mean === undefined) {
      return "-";
    }
    if (metricValue.std === null || metricValue.std === undefined) {
      return formatNumber(metricValue.mean);
    }
    return `${formatNumber(metricValue.mean)} ± ${formatNumber(metricValue.std)}`;
  }

  function getDirectionForMetric(key) {
    const m = schema.find((item) => item.key === key);
    return m ? m.direction : "max";
  }

  function getBestOrderForKey(key) {
    if (key === "method") return "asc";
    return getDirectionForMetric(key) === "min" ? "asc" : "desc";
  }

  function getRowsForCurrentScope() {
    const scope = scopeSelect.value;
    if (scope === "__global__") return [...globalRows];
    return [...(byTask[scope] || [])];
  }

  function isIncludedMethod(row) {
    const method = (row?.method || "").trim().toLowerCase();
    return !EXCLUDED_METHODS.has(method);
  }

  function getSortIndicator(key) {
    if (sortState.key !== key) return "";
    return sortState.order === "asc" ? " (sorted: low -> high)" : " (sorted: high -> low)";
  }

  function compareRows(a, b, key, order) {
    if (key === "method") {
      const cmp = a.method.localeCompare(b.method);
      return order === "asc" ? cmp : -cmp;
    }
    const aValue = a.metrics?.[key]?.mean;
    const bValue = b.metrics?.[key]?.mean;
    const aMissing = aValue === null || aValue === undefined || Number.isNaN(aValue);
    const bMissing = bValue === null || bValue === undefined || Number.isNaN(bValue);
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;
    if (aValue === bValue) return 0;
    return order === "asc" ? aValue - bValue : bValue - aValue;
  }

  function sortRows(rows) {
    rows.sort((a, b) => compareRows(a, b, sortState.key, sortState.order));
  }

  function onHeaderClick(key) {
    if (sortState.key === key) {
      sortState.order = sortState.order === "asc" ? "desc" : "asc";
    } else {
      sortState.key = key;
      sortState.order = getBestOrderForKey(key);
    }
    renderTable();
  }

  function renderHeader() {
    const tr = document.createElement("tr");

    const methodTh = document.createElement("th");
    methodTh.textContent = `Method${getSortIndicator("method")}`;
    methodTh.style.cursor = "pointer";
    methodTh.onclick = () => onHeaderClick("method");
    tr.appendChild(methodTh);

    for (const metric of schema) {
      const th = document.createElement("th");
      th.style.cursor = "pointer";
      const direction = metric.direction === "min" ? "↓" : "↑";
      th.textContent = `${metric.label} ${direction}${getSortIndicator(metric.key)}`;
      th.onclick = () => onHeaderClick(metric.key);
      tr.appendChild(th);
    }

    tableHead.innerHTML = "";
    tableHead.appendChild(tr);
  }

  function renderBody(rows) {
    tableBody.innerHTML = "";
    for (const row of rows) {
      const tr = document.createElement("tr");
      const methodTd = document.createElement("td");
      methodTd.textContent = row.method;
      tr.appendChild(methodTd);

      for (const metric of schema) {
        const td = document.createElement("td");
        td.textContent = formatMetricCell(row.metrics?.[metric.key]);
        tr.appendChild(td);
      }
      tableBody.appendChild(tr);
    }
  }

  function renderHint() {
    const metric = sortState.key === "method"
      ? { label: "Method", direction: "max" }
      : schema.find((m) => m.key === sortState.key);
    if (!metric) {
      hint.textContent = "";
      return;
    }
    const directionText = metric.direction === "min" ? "lower is better" : "higher is better";
    hint.textContent = `Sorted by ${metric.label} (${sortState.order.toUpperCase()}, ${directionText}). Click a column to sort; first click applies best-direction sorting.`;
  }

  function renderTable() {
    renderHeader();
    const rows = getRowsForCurrentScope().filter(isIncludedMethod);
    sortRows(rows);
    renderBody(rows);
    renderHint();
  }

  function renderScopeOptions() {
    scopeSelect.innerHTML = "";
    const globalOption = document.createElement("option");
    globalOption.value = "__global__";
    globalOption.text = "Global (all tasks)";
    scopeSelect.appendChild(globalOption);

    Object.keys(byTask).forEach((taskName) => {
      const option = document.createElement("option");
      option.value = taskName;
      option.text = taskName;
      scopeSelect.appendChild(option);
    });

    scopeSelect.value = "__global__";
  }

  async function loadLeaderboardData() {
    try {
      const [schemaRes, byTaskRes, globalRes] = await Promise.all([
        fetch("./static/data/leaderboard_schema.json"),
        fetch("./static/data/leaderboard_by_task.json"),
        fetch("./static/data/leaderboard_global.json"),
      ]);

      schema = await schemaRes.json();
      byTask = await byTaskRes.json();
      globalRows = await globalRes.json();

      if (schema.length > 0 && !schema.find((m) => m.key === sortState.key)) {
        sortState = { key: schema[0].key, order: getBestOrderForKey(schema[0].key) };
      }

      renderScopeOptions();
      renderTable();
    } catch (error) {
      hint.textContent = "Failed to load leaderboard data.";
      console.error("Failed to load leaderboard data:", error);
    }
  }

  scopeSelect.addEventListener("change", renderTable);
  window.addEventListener("DOMContentLoaded", loadLeaderboardData);
})();
