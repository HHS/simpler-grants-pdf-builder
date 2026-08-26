(() => {
  const REQUEST_TIMEOUT_MS = 15000;
  const panel = document.getElementById("readability-metrics-panel");
  if (!panel) return;

  const summary = panel.querySelector(":scope > summary");
  const button = document.getElementById("calculate-readability-metrics");
  const status = document.getElementById("readability-metrics-status");
  const results = document.getElementById("readability-metrics-results");
  const goalPolicyElement = document.getElementById("readability-metric-goals");
  const scopeContainer = panel.querySelector("[data-metrics-scope-container]");
  const scopeSummary = panel.querySelector("[data-metrics-scope-summary]");
  const summaryStatus = panel.querySelector("[data-metrics-summary-status]");
  const warnings = panel.querySelector("[data-metrics-warnings]");
  const warningCount = panel.querySelector("[data-metrics-warning-count]");
  const warningsList = panel.querySelector("[data-metrics-warnings-list]");
  let hasRequestedMetrics = false;
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
    const optionalCard = container.closest("[data-optional-metric-card]");
    if (optionalCard) {
      const available =
        metric.status === "calculated" && typeof metric.value === "number";
      optionalCard.hidden = !available;
      if (!available) return;
    }

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
    container
      .querySelectorAll("[data-metric-goal-item]")
      .forEach((item) => item.remove());
    const configuredGoals = goalPolicy[metricId];
    const goals = Array.isArray(configuredGoals)
      ? configuredGoals
      : configuredGoals
        ? [configuredGoals]
        : [];
    if (
      goals.length === 0 ||
      metric.status !== "calculated" ||
      typeof metric.value !== "number"
    ) {
      return;
    }

    goals.forEach((goal) => {
      const goalText = document.createElement("dd");
      goalText.className =
        "font-sans-3xs text-base-dark margin-left-0 margin-top-1";
      goalText.dataset.metricGoalItem = "";
      container.append(goalText);
      if (goal.operator === "at_most_by_category") {
        const minimum = formatValue(metricId, { value: goal.minimum });
        const maximum = formatValue(metricId, { value: goal.maximum });
        goalText.textContent = `${goal.label}: ${minimum}–${maximum}`;
      } else {
        const direction = goal.operator === "at_most" ? "or lower" : "or higher";
        goalText.textContent = `${goal.label}: ${formatValue(metricId, goal)} ${direction}`;
      }

      const assessment = document.createElement("dd");
      assessment.className = "margin-left-0 margin-top-1";
      assessment.dataset.metricGoalItem = "";
      container.append(assessment);
      let assessmentText;
      let assessmentClass;
      if (goal.operator === "at_most_by_category") {
        if (metric.value <= goal.minimum) {
          assessmentText = "Within target";
          assessmentClass = "bg-success-lighter";
        } else if (metric.value > goal.maximum) {
          assessmentText = "Needs improvement";
          assessmentClass = "bg-warning-lighter";
        } else {
          assessmentText = "Check NOFO type";
          assessmentClass = "bg-accent-cool-lighter";
        }
      } else {
        const withinGoal =
          goal.operator === "at_most"
            ? metric.value <= goal.value
            : metric.value >= goal.value;
        assessmentText = withinGoal ? "Within target" : "Needs improvement";
        assessmentClass = withinGoal
          ? "bg-success-lighter"
          : "bg-warning-lighter";
      }
      assessment.className =
        "usa-tag display-inline-block width-auto text-base-dark margin-left-0 " +
        assessmentClass;
      assessment.textContent = assessmentText;
    });
  };

  const metricForDisplay = (metricId, metrics = {}) => {
    if (metricId !== "sentences_per_paragraph") {
      return metrics[metricId];
    }
    const sentenceMetric = metrics.words_per_sentence || {};
    return {
      ...sentenceMetric,
      value: sentenceMetric.components?.sentences_per_paragraph,
    };
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
      scopeContainer.hidden = true;
      return;
    }

    const format = new Intl.NumberFormat();
    let summary =
      `Word count includes all NOFO text: ${format.format(documentWords)} words. ` +
      `Sentence-based formulas use ${format.format(sentenceWords)} words in ` +
      `${format.format(sentenceCount)} complete sentences.`;
    if (documentWords >= sentenceWords && documentWords > 0) {
      const excludedWords = documentWords - sentenceWords;
      const excludedPercentage = new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 1,
      }).format((100 * excludedWords) / documentWords);
      summary +=
        ` The remaining ${format.format(excludedWords)} words ` +
        `(${excludedPercentage}%) are in text that does not form complete ` +
        `sentences, such as some headings, labels, list items, table cells, ` +
        `and other fragments, so sentence-based scores exclude them.`;
    }
    scopeSummary.textContent = summary;
    scopeContainer.hidden = false;
  };

  const calculateMetrics = async () => {
    hasRequestedMetrics = true;
    button.disabled = true;
    status.textContent = "Calculating metrics…";
    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS,
    );

    try {
      // Calculating stores a snapshot, so this is a mutating request.
      const response = await fetch(panel.dataset.metricsEndpoint, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-CSRFToken": panel.dataset.csrfToken,
        },
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
        showMetric(metricId, metricForDisplay(metricId, payload.metrics));
      });

      showScopeSummary(payload.metrics);
      showWarnings(payload.warnings);
      results.hidden = false;
      status.textContent = "Calculated for the current revision.";
      summaryStatus.textContent = "Calculated";
      button.textContent = "Recalculate";
      button.classList.add("usa-button--outline");
    } catch (error) {
      results.hidden = true;
      scopeContainer.hidden = true;
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
  };

  button.addEventListener("click", calculateMetrics);
  panel.addEventListener("toggle", () => {
    if (panel.open && !hasRequestedMetrics) {
      void calculateMetrics();
    }
  });
})();
