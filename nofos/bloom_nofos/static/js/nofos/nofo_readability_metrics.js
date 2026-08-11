(() => {
  const panel = document.getElementById("readability-metrics-panel");
  if (!panel) return;

  const button = document.getElementById("calculate-readability-metrics");
  const status = document.getElementById("readability-metrics-status");
  const results = document.getElementById("readability-metrics-results");
  const profile = panel.querySelector("[data-metrics-profile]");
  const warnings = panel.querySelector("[data-metrics-warnings]");
  const warningsList = panel.querySelector("[data-metrics-warnings-list]");

  const formatValue = (metricId, metric) => {
    if (metric.value === null || metric.value === undefined) return "—";
    if (metricId === "word_count") {
      return new Intl.NumberFormat().format(metric.value);
    }
    const value = new Intl.NumberFormat(undefined, {
      maximumFractionDigits: 2,
    }).format(metric.value);
    return metricId === "passive_sentence_percentage" ? `${value}%` : value;
  };

  const showMetric = (metricId, metric = {}) => {
    const container = panel.querySelector(`[data-metric-id="${metricId}"]`);
    if (!container) return;

    container.querySelector("[data-metric-value]").textContent = formatValue(
      metricId,
      metric,
    );
    const metricStatus = container.querySelector("[data-metric-status]");
    metricStatus.textContent = metric.reason || metric.status || "Unavailable";
  };

  const showWarnings = (items = []) => {
    warningsList.replaceChildren();
    items.forEach((item) => {
      const listItem = document.createElement("li");
      listItem.textContent = item.message;
      warningsList.append(listItem);
    });
    warnings.hidden = items.length === 0;
  };

  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Calculating metrics…";

    try {
      const response = await fetch(panel.dataset.metricsEndpoint, {
        headers: { Accept: "application/json" },
      });
      let payload = {};
      try {
        payload = await response.json();
      } catch {
        // The status code still supplies a useful fallback for non-JSON errors.
      }

      if (!response.ok) {
        throw new Error(payload.message || `Request failed (${response.status}).`);
      }

      panel.querySelectorAll("[data-metric-id]").forEach((container) => {
        const metricId = container.dataset.metricId;
        showMetric(metricId, payload.metrics?.[metricId]);
      });

      if (payload.profile) {
        profile.textContent = `${payload.profile.id}@${payload.profile.version} (${payload.profile.status})`;
      }
      showWarnings(payload.warnings);
      results.hidden = false;
      status.textContent = "Metrics calculated for the current NOFO revision.";
      button.textContent = "Recalculate metrics";
    } catch (error) {
      status.textContent = `Metrics could not be calculated. ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
})();
