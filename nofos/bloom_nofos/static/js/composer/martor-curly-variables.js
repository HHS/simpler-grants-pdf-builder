// Curly variables: highlighting + live list (Ace/Martor)
// -----------------------------------------------------
// - Highlights {curly placeholders} inside the Ace editor
// - Renders a live, deduped list of those variables into #curly-variables--list
// - Shares one regex + one init/poll loop for both behaviors
//
(function () {
  "use strict";

  // ===========================================================================
  // SHARED CONFIG / HELPERS
  // ===========================================================================

  // Keep in sync with Python: r"(?<!\\)\{(?![:.#])([^{}]*\S[^{}]*)\}"
  const CURLY_VARIABLE_PATTERN_JS = /(?<!\\)\{(?![:.#])[^{}]*\S[^{}]*\}/g;

  // Token types from Ace's Markdown mode we consider "textual" (safe to split)
  const TEXT_TOKEN_TYPES = [
    "text.xml",
    "text",
    "heading",
    "list",
    "string.blockquote",
  ];

  // Target container for the inline list appended after your description sentence
  const LIST_CONTAINER_ID = "curly-variables--list";

  /**
   * Debounce a function call.
   * Ensures `fn` runs only after `ms` milliseconds have passed without a new call.
   */
  function debounce(fn, ms) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  // ===========================================================================
  // MODULE A — ACE HIGHLIGHTING (tokenizer wrapper)
  // ===========================================================================
  // This portion of the script adds custom syntax highlighting for curly braces
  // {like this} in the Martor markdown editor (which uses the Ace editor internally).
  //
  // We can't modify Ace's highlighting rules directly (they're compiled), but we
  // CAN intercept the tokenizer and post-process its output. This is called the
  // "tokenizer wrapper" pattern.
  //
  // THE STRATEGY:
  //   1. Wait for the Ace editor to load and render
  //   2. Get the editor's current tokenizer (handles markdown syntax)
  //   3. Wrap it with our own function that adds extra processing
  //   4. Our wrapper looks for {curly braces} in text tokens and splits them
  //   5. Mark curly brace sections as "variable.curly" tokens
  //   6. Force the editor to re-render with our new tokens
  //   7. CSS (separate file) styles .ace_variable.ace_curly elements

  /**
   * Split a token containing {curly braces} into multiple tokens.
   *
   * Example input token:
   *   { type: "text.xml", value: "Hello {world} here" }
   *
   * Example output tokens:
   *   [
   *     { type: "text.xml", value: "Hello " },
   *     { type: "variable.curly", value: "{world}" },
   *     { type: "text.xml", value: " here" }
   *   ]
   */
  function splitTokenOnCurlyBraces(token) {
    const matches = [];
    let match;
    CURLY_VARIABLE_PATTERN_JS.lastIndex = 0;

    while ((match = CURLY_VARIABLE_PATTERN_JS.exec(token.value)) !== null) {
      matches.push({ index: match.index, text: match[0] });
    }

    // If not matches, return original token unchanged
    if (matches.length === 0) return [token];

    const newTokens = [];
    let lastIndex = 0;

    matches.forEach((m) => {
      if (m.index > lastIndex) {
        newTokens.push({
          type: token.type,
          value: token.value.substring(lastIndex, m.index),
        });
      }
      // Add the variable with included curly braces as a special "variable.curly" token
      // This is what CSS will target with .ace_variable.ace_curly
      newTokens.push({ type: "variable.curly", value: m.text });
      lastIndex = m.index + m.text.length;
    });

    if (lastIndex < token.value.length) {
      newTokens.push({
        type: token.type,
        value: token.value.substring(lastIndex),
      });
    }

    return newTokens;
  }

  /**
   * Wrap the original tokenizer to add curly brace highlighting.
   *
   * This creates a "proxy" tokenizer that:
   *   1. Calls the original tokenizer to get markdown tokens
   *   2. Post-processes those tokens to split out curly braces
   *   3. Returns the enhanced token list
   */
  function wrapTokenizer(originalTokenizer) {
    return {
      getLineTokens: function (line, startState) {
        const result = originalTokenizer.getLineTokens(line, startState);
        const processedTokens = [];

        result.tokens.forEach((token) => {
          const isTextToken = TEXT_TOKEN_TYPES.includes(token.type);
          if (isTextToken && token.value) {
            processedTokens.push(...splitTokenOnCurlyBraces(token));
          } else {
            processedTokens.push(token);
          }
        });

        return { tokens: processedTokens, state: result.state };
      },

      // Proxy required tokenizer methods so Ace remains happy
      $rules: originalTokenizer.$rules,
      getState: originalTokenizer.getState,
      getStateNames: originalTokenizer.getStateNames,
    };
  }

  /**
   * Apply curly brace highlighting to the Ace editor.
   *
   * This is the main setup function that:
   *   1. Gets the editor's current mode and tokenizer
   *   2. Wraps the tokenizer with our custom logic
   *   3. Forces the editor to re-tokenize and re-render everything
   *   4. Sets up change handlers to maintain highlighting as user types
   */
  function applyHighlighting(editor) {
    const session = editor.getSession();
    const mode = session.getMode();

    // Only apply to Markdown mode, and only once
    if (
      !mode.$id?.includes("markdown") ||
      mode.getTokenizer().__curlyVarsWrapped
    ) {
      return;
    }

    const wrappedTokenizer = wrapTokenizer(mode.getTokenizer());
    wrappedTokenizer.__curlyVarsWrapped = true; // mark as installed
    mode.getTokenizer = () => wrappedTokenizer;

    // Force re-tokenization & re-render
    session.bgTokenizer.setTokenizer(wrappedTokenizer);
    session.bgTokenizer.fireUpdateEvent(0, session.getLength() - 1);
    session.bgTokenizer.start(0);
    editor.renderer.updateFull();

    // Keep the viewport fresh on edits
    session.on("change", (delta) => {
      setTimeout(() => {
        editor.renderer.updateLines(
          delta.start.row,
          delta.end.row + (delta.lines?.length || 1)
        );
      }, 10);
    });

    console.log("[curly-variables] Highlighting applied");
  }

  // ===========================================================================
  // MODULE B — VARIABLE LIST (extract + render to #curly-variables--list)
  // ===========================================================================

  /**
   * Extract unique curly variables from a text blob using the shared regex.
   * Keeps first-seen order; returns the inside text (without braces) trimmed.
   */
  function extractCurlyVariables(text) {
    const vars = [];
    const seen = new Set();
    CURLY_VARIABLE_PATTERN_JS.lastIndex = 0;

    let m;
    while ((m = CURLY_VARIABLE_PATTERN_JS.exec(text)) !== null) {
      // m[0] is "{ ... }" including braces
      const inside = m[0].slice(1, -1).trim();
      if (!seen.has(inside)) {
        seen.add(inside);
        vars.push(inside);
      }
    }
    return vars;
  }

  /**
   * Render variables inline into #curly-variables--list as:
   *   ": <span class='curly-var'>{one}</span>, <span class='curly-var'>{two}</span>, ..."
   * If none exist, keep the span empty so your label sentence reads naturally.
   */
  function renderVariableList(vars) {
    const container = document.getElementById(LIST_CONTAINER_ID);
    if (!container) return;

    // Clear previous
    container.textContent = "";

    if (vars.length === 0) {
      // Keep empty to let the sentence read naturally with the trailing period.
      return;
    }

    // Prefix ": "
    container.appendChild(document.createTextNode(": "));

    vars.forEach((v, i) => {
      const span = document.createElement("span");
      span.className = "curly-var font-mono-xs";
      span.textContent = `{${v}}`; // show braces
      container.appendChild(span);

      if (i < vars.length - 1) {
        container.appendChild(document.createTextNode(", "));
      }
    });
  }

  /**
   * Bind live updates so the list reflects current editor content.
   * Debounced to avoid excessive DOM work during rapid typing.
   */
  function attachVariableListUpdater(editor) {
    const session = editor.getSession();
    const update = debounce(() => {
      const text = session.getValue();
      const vars = extractCurlyVariables(text);
      renderVariableList(vars);
    }, 80);

    // Initial render after first paint
    editor.renderer.once("afterRender", () => {
      setTimeout(update, 0);
    });

    // Update on typical change signals
    session.on("change", update);
    session.on("changeMode", update);
    editor.on("input", update);

    console.log("[curly-variables] Variable list active");
  }

  // ===========================================================================
  // BOOTSTRAP (shared init for both modules)
  // ===========================================================================

  /**
   * Poll for Ace + the editor element; once ready, attach:
   *  - Module A (highlighting via tokenizer wrapper)
   *  - Module B (variable list updater)
   */
  function init(attempts = 0) {
    const ace = window.ace;
    const editorElement = document.querySelector(".ace_editor");

    if (ace && editorElement) {
      try {
        const editor = ace.edit(editorElement);

        // After first render, apply both features in a stable order
        editor.renderer.once("afterRender", () => {
          // Short delay to ensure mode/tokenizer is ready
          setTimeout(() => {
            // MODULE A: Ace highlighting
            applyHighlighting(editor);
            // MODULE B: Inline variable list
            attachVariableListUpdater(editor);
          }, 50);
        });
      } catch (e) {
        console.error("[curly-variables] Init error:", e);
      }
    } else if (attempts < 50) {
      // Poll every 100ms for up to 5s
      setTimeout(() => init(attempts + 1), 100);
    }
  }

  init();
})();
