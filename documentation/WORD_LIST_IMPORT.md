# Word list import and editing

Use native Word lists for numbered or bulleted content. Builder preserves
supported source markers and nesting on a new import or explicit reimport.
Opening an existing NOFO does not convert its saved lists.

## Supported representations

Simple standalone bullets and ordinary decimal lists remain readable Markdown:

```markdown
1. Review eligibility.
2. Prepare the application.

* Include the budget.
    + Explain each cost.
```

Builder retains semantic HTML when a list tree needs letter/Roman markers,
explicit decimal descendants or non-one starts. Separate adjacent lists also
remain HTML, including a bullet list immediately followed by a numbered list
(or the reverse), so their boundaries and markers survive rendering. Keep nested
lists inside their parent list item when editing this representation:

```html
<ol type="a">
  <li>First activity
    <ol type="i">
      <li>First subactivity
        <ol type="1">
          <li>First criterion</li>
        </ol>
      </li>
    </ol>
  </li>
</ol>
```

Supported ordered types are `1`, `a`, `A`, `i` and `I`. A `start="4"`
attribute starts at the fourth value of the selected type. Do not add a literal
`1)` prefix inside an automatically numbered item: that displays two markers.
Decimal Word markers such as `1)` may normalize to `1.`. Custom punctuation and
compound markers such as `1.2.3` are not equivalent to ordinary HTML numbering.

## Check after import

Compare list types, order and nesting with the source. Check continuation
paragraphs and places where numbering restarts. Use the subsection's **Edit**
action, inspect its preview and select **Save subsection** after corrections.
Then check the generated PDF, including any list spanning a page boundary.

If Builder displays **Check list numbering**, the document contains numbering
it could not fully preserve. The import is not blocked. Compare the affected
lists with Word and correct their markers or nesting in the subsection editor.
For a new import, first save the name and open the NOFO from **All NOFOs**.

Typed marker-like text and inline enumerations remain text. This change does
not guess list structure from prose or repair every pasted/manual list. Native
lists are preferable, but they do not guarantee fidelity for unsupported custom
formats or ambiguous continuation indentation.

The narrowly matched ACF required-alignment repair remains intentional: its
three groups become decimal lists starting at 1, 2 and 4. Other source-typed
lists are not restyled globally. Legacy untyped content retains the existing
depth-based styling.

The maintained repository editor guidance is [EDITOR_TASKS.md](EDITOR_TASKS.md).
This implementation does not change externally maintained agency content
guides or make support claims on their behalf.
