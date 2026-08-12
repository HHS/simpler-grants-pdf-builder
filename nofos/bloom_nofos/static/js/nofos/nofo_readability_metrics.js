(() => {
  const REQUEST_TIMEOUT_MS = 15000;
  const panel = document.getElementById("readability-metrics-panel");
  if (!panel) return;

  const summary = panel.querySelector(":scope > summary");
  const button = document.getElementById("calculate-readability-metrics");
  const status = document.getElementById("readability-metrics-status");
  const results = document.getElementById("readability-metrics-results");
  const goalPolicyElement = document.getElementById("readability-metric-goals");
  const scopeSummary = panel.querySelector("[data-metrics-scope-summary]");
  const summaryStatus = panel.querySelector("[data-metrics-summary-status]");
  const warnings = panel.querySelector("[data-metrics-warnings]");
  const warningCount = panel.querySelector("[data-metrics-warning-count]");
  const warningsList = panel.querySelector("[data-metrics-warnings-list]");
  let goalPolicy = {};
  if (goalPolicyElement) {
    try {
      goalPolicy = JSON.parse(goalPolicyElement.textContent);
    } catch {
      // Server-side validation normally prevents malformed configuration.
    }
  }

  const syncExpandedState = () => {
    summary.setAttribute("aria-expanded", String(panel.open));
  };
  panel.addEventListener("toggle", syncExpandedState);
  syncExpandedState();

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
    metricStatus.classList.toggle("usa-sr-only", metric.status === "calculated");
    showGoal(container, metricId, metric);
  };

  const showGoal = (container, metricId, metric) => {
    const existingGoal = container.querySelector("[data-metric-goal]");
    const existingAssessment = container.querySelector(
      "[data-metric-goal-assessment]",
    );
    const goal = goalPolicy[metricId];
    if (
      !goal ||
      metric.status !== "calculated" ||
      typeof metric.value !== "number"
    ) {
      if (existingGoal) existingGoal.hidden = true;
      if (existingAssessment) existingAssessment.hidden = true;
      return;
    }

    const goalText = existingGoal || document.createElement("dd");
    if (!existingGoal) {
      goalText.className = "font-sans-2xs text-base margin-left-0 margin-top-1";
      goalText.dataset.metricGoal = "";
      container.append(goalText);
    }
    const direction = goal.operator === "at_most" ? "or lower" : "or higher";
    goalText.textContent = `${goal.label}: ${formatValue(metricId, goal)} ${direction}`;
    goalText.hidden = false;

    const assessment = existingAssessment || document.createElement("dd");
    if (!existingAssessment) {
      assessment.className = "font-sans-2xs text-bold margin-left-0";
      assessment.dataset.metricGoalAssessment = "";
      container.append(assessment);
    }
    const withinGoal =
      goal.operator === "at_most"
        ? metric.value <= goal.value
        : metric.value >= goal.value;
    assessment.textContent = withinGoal
      ? "Within configured goal"
      : "Review against configured goal";
    assessment.hidden = false;
  };

  const showWarnings = (items = []) => {
    warningsList.replaceChildren();
    items.forEach((item) => {
      const listItem = document.createElement("li");
      listItem.textContent = item.message;
      warningsList.append(listItem);
    });
    warningCount.textContent = items.length;
    warnings.hidden = items.length === 0;
  };

  const showScopeSummary = (metrics = {}) => {
    const documentWords = metrics.word_count?.value;
    const sentenceComponents = metrics.words_per_sentence?.components;
    const sentenceWords = sentenceComponents?.word_count;
    const sentenceCount = sentenceComponents?.sentence_count;

    if (
      documentWords === null ||
      documentWords === undefined ||
      sentenceWords === null ||
      sentenceWords === undefined ||
      sentenceCount === null ||
      sentenceCount === undefined
    ) {
      scopeSummary.hidden = true;
      return;
    }

    const format = new Intl.NumberFormat();
    scopeSummary.textContent =
      `Sentence-based metrics use ${format.format(sentenceWords)} words in ` +
      `${format.format(sentenceCount)} complete sentences. Total word count ` +
      `uses the broader document scope: ${format.format(documentWords)} words.`;
    scopeSummary.hidden = false;
  };

  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Calculating metrics…";
    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS,
    );

    try {
      const response = await fetch(panel.dataset.metricsEndpoint, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
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

      showScopeSummary(payload.metrics);
      showWarnings(payload.warnings);
      results.hidden = false;
      status.textContent = "Metrics calculated for the current NOFO revision.";
      summaryStatus.textContent = "Calculated";
      button.textContent = "Recalculate metrics";
    } catch (error) {
      results.hidden = true;
      scopeSummary.hidden = true;
      showWarnings([]);
      const message =
        error.name === "AbortError"
          ? "The calculation took too long. Try again."
          : error.message;
      status.textContent = `Metrics could not be calculated. ${message}`;
      summaryStatus.textContent = "Unable to calculate";
    } finally {
      window.clearTimeout(timeoutId);
      button.disabled = false;
    }
  });
})();
