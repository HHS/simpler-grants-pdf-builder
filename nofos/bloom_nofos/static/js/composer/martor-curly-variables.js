// HIGH-LEVEL OVERVIEW:
// ====================
// This script adds custom syntax highlighting for curly braces {like this} in
// the Martor markdown editor (which uses the Ace editor internally).
//
// WHY THIS APPROACH:
// Ace editor has a two-stage rendering process:
//   1. TOKENIZATION: Text is broken into "tokens" (e.g., "bold", "italic", "text")
//   2. RENDERING: Each token type gets CSS classes (e.g., .ace_string_emphasis)
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
//
(function () {
  "use strict";

  const CURLY_VARIABLE_PATTERN_JS = /(?<!\\)\{[^{}]*\S[^{}]*\}/g;
  const TEXT_TOKEN_TYPES = [
    "text.xml",
    "text",
    "heading",
    "list",
    "string.blockquote",
  ];

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
    // Find all {curly brace} matches in this token's text
    const matches = [];
    let match;
    CURLY_VARIABLE_PATTERN_JS.lastIndex = 0;

    while ((match = CURLY_VARIABLE_PATTERN_JS.exec(token.value)) !== null) {
      matches.push({ index: match.index, text: match[0] });
    }

    // None found? Return original token unchanged
    if (matches.length === 0) return [token];

    // Build new token array by splitting around matches
    const newTokens = [];
    let lastIndex = 0;

    matches.forEach((match) => {
      // Add any text BEFORE the curly brace (if there is any)
      if (match.index > lastIndex) {
        newTokens.push({
          type: token.type, // Keep original token type for this text
          value: token.value.substring(lastIndex, match.index),
        });
      }

      // Add the curly brace itself as a special "variable.curly" token
      // This is what CSS will target with .ace_variable.ace_curly
      newTokens.push({ type: "variable.curly", value: match.text });
      lastIndex = match.index + match.text.length;
    });

    // Add any remaining text AFTER the last curly brace
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
        // Step 1: Get tokens from original markdown tokenizer
        const result = originalTokenizer.getLineTokens(line, startState);
        const processedTokens = [];

        // Step 2: Process each token to find and split curly braces
        result.tokens.forEach((token) => {
          const isTextToken = TEXT_TOKEN_TYPES.includes(token.type);
          if (isTextToken && token.value) {
            // This is a text token - scan it for {curly braces}
            processedTokens.push(...splitTokenOnCurlyBraces(token));
          } else {
            processedTokens.push(token);
          }
        });

        return { tokens: processedTokens, state: result.state };
      },

      // Proxy required tokenizer methods to the original
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

    // Guard: Only apply to markdown mode, and only one time
    if (
      !mode.$id?.includes("markdown") ||
      mode.getTokenizer().__curlyVarsWrapped
    ) {
      return;
    }

    // Create wrapped tokenizer (our tokenizer wrapping the markdown tokenizer)
    const wrappedTokenizer = wrapTokenizer(mode.getTokenizer());
    // Mark it so we don't wrap it again if this function runs multiple times
    wrappedTokenizer.__curlyVarsWrapped = true;
    // Replace the mode's tokenizer getter to return our wrapped version
    mode.getTokenizer = () => wrappedTokenizer;

    // ===== FORCE RE-TOKENIZATION AND RE-RENDER =====
    // The editor has already tokenized the content with the old tokenizer.
    // We need to force it to re-tokenize everything with our new tokenizer.

    // Tell the background tokenizer to use our new tokenizer
    session.bgTokenizer.setTokenizer(wrappedTokenizer);
    // Fire an update event to signal that tokens have changed
    session.bgTokenizer.fireUpdateEvent(0, session.getLength() - 1);
    // Restart background tokenization from the beginning
    session.bgTokenizer.start(0);
    // Force the renderer to redraw everything on screen
    editor.renderer.updateFull();

    // Re-render lines when content changes
    session.on("change", (delta) => {
      // Small delay to let the tokenizer process first
      setTimeout(() => {
        editor.renderer.updateLines(
          delta.start.row,
          delta.end.row + (delta.lines?.length || 1)
        );
      }, 10);
    });

    console.log("[curly-variables] Highlighting applied");
  }

  /**
   * Wait for the Ace editor to be ready, then apply highlighting.
   *
   * This polls for the editor to exist because:
   *   1. Our script might load before Martor initializes the editor
   *   2. We need the editor to be fully rendered before modifying it
   */
  function init(attempts = 0) {
    const ace = window.ace;
    const editorElement = document.querySelector(".ace_editor");

    if (ace && editorElement) {
      try {
        const editor = ace.edit(editorElement);
        // Wait for the editor to render at least once (ensures the editor is fully initialized)
        editor.renderer.once("afterRender", () => {
          setTimeout(() => applyHighlighting(editor), 50);
        });
      } catch (e) {
        console.error("[curly-vars] Error:", e);
      }
    } else if (attempts < 50) {
      // Editor not ready yet - try again in 100ms
      // Give up after 50 attempts (5 seconds total)
      setTimeout(() => init(attempts + 1), 100);
    }
  }

  init();
})();
