# HTML to DOCX solution

- **Status:** Active
- **Last Modified:** 2026-01-12
- **Deciders:** Julia Hogan, Paul Craig

## Context and Problem Statement

The goal of this ADR is to select a solution for converting HTML documents to DOCX format for the NOFO Composer. Users need to be able to export their NOFO documents as Word files that maintain formatting, styles, and accessibility features. The exported documents must also be re-importable into the system, creating a round-trip workflow.

We need a solution that can handle complex HTML with:
- Tables with styling (ideally also custom column widths)
- Nested lists (ordered and unordered)
- Links
- Inline images (base64 encoded)
- Text formatting (bold, italic, colors)
- Page breaks
- Custom document elements like callout boxes

## Decision Drivers <!-- RECOMMENDED -->

- **Formatting fidelity:** How well does the conversion preserve the visual design and styling from HTML to DOCX?
- **Round-trip capability:** Can documents be exported to DOCX and then successfully re-imported into the system?
- **Semantic styling:** Does the output use proper Word styles (e.g., "Heading 1", "List Bullet") rather than just visual formatting?
- **Ease of integration:** How straightforward is it to integrate the solution with our Python/Django application?
- **Cost:** What are the pricing tiers and how do they align with our expected volume?
- **Security & compliance:** Does the solution meet GDPR and federal security requirements?
- **Reliability & support:** Is the service actively maintained with responsive support?

## Options Tested

We evaluated five HTML-to-DOCX conversion services:

1. [ConvertHub](https://converthub.com/)
2. [Convert API](https://www.convertapi.com/)
3. [Groupdocs.Conversion cloud API](https://products.groupdocs.cloud/conversion/curl/html-to-docx/)
4. [Cloudconvert](https://cloudconvert.com/html-to-docx)
5. [Grabzit](https://grabz.it/html-to-word-docx-api/)

### Approach
A sample NOFO HTML document was created from the preview view in NOFO composer. All styles were in-lined to make them available to the various conversion tools and APIs. This test document was then provided as input to all conversion services, following tool-specific instructions for testing. The resulting output docx files were inspected in Microsoft word, and if apparently viable, re-imported into NOFO Builder.

## Decision Outcome <!-- REQUIRED -->

Chosen option: **Grabzit**, which is a SaaS API service that converts HTML to DOCX format.

- It preserves formatting, colors, tables, and lists significantly better than other tested solutions.
- The export/convert/reimport workflow works well, enabling round-trip document editing.
- It provides a Python library for easy API integration.
- Very affordable pricing ($6.99 for 5,000 conversions/month) that fits our anticipated volume.
- GDPR compliant with encryption at rest using customer-provided keys.
- Actively maintained service with responsive community support.

While Grabzit has some limitations around semantic styling (e.g., list items show as "Normal" style rather than "List 1"), the overall quality of the conversion and successful round-trip capability make it the best option. The time savings compared to building a custom solution using python-docx will be substantial.

### Known Limitations

Areas that will require mitigation or are acceptable edge cases:

- **Semantic styling:** Generated DOCX uses "Normal" style for most content rather than semantic styles like "Heading 1" or "List Bullet". This doesn't break reimport but may affect user workflows.
- **Classnames lost:** CSS classes (e.g., for table column widths) are not preserved in the conversion.
- **Footnotes:** Not rendered semantically, considered an edge case.
- **Documentation quality:** Grabzit's documentation is limited, which could complicate troubleshooting complex formatting issues.

Compatibility considerations to address:
- Page breaks
- Callout boxes
- Document metadata
- Table formatting (acceptable if classnames are lost)
- Broken links in source HTML
- Section headings (H2s may need manual handling as section pages should not be exported)

## Evaluated Options

### [ConvertHub](https://converthub.com/)

ConvertHub is an HTML to DOCX conversion service.

- **Pros**
  - N/A (could not successfully test)
- **Cons**
  - Returned corrupted/malformed DOCX files that could not be opened
  - Not viable for production use

### [Convert API](https://www.convertapi.com/)

Convert API provides document conversion services via REST API.

- **Pros**
  - Successfully converted HTML to DOCX
  - Basic document structure preserved
- **Cons**
  - No formatting or styles in output
  - Plain text conversion only
  - Not suitable for maintaining document fidelity

### [Groupdocs.Conversion cloud API](https://products.groupdocs.cloud/conversion/curl/html-to-docx/)

Groupdocs offers a cloud-based document conversion API.

- **Pros**
  - Potentially robust solution with responsive support
- **Cons**
  - Unable to convert test documents successfully
  - Returned vague "internal error" messages or "invalid or corrupted" errors for valid HTML
  - Would require significant debugging and support intervention
  - Out of scope for current investigation

### [Cloudconvert](https://cloudconvert.com/html-to-docx)

Cloudconvert is a file conversion platform supporting many formats.

- **Pros**
  - Successfully converted HTML to DOCX
  - Basic document structure preserved
- **Cons**
  - No formatting or styles in output
  - Plain text conversion only
  - Not suitable for maintaining document fidelity

### [Grabzit](https://grabz.it/html-to-word-docx-api/) ✓ SELECTED

Grabzit is an HTML-to-DOCX conversion service with Python client library support.

- **Pros**
  - **Excellent formatting preservation:** Fonts with colors, styled tables, and properly formatted lists
  - **Round-trip capability:** Export/convert/reimport workflow works well
  - **Python library available:** [Official Python client](https://grabz.it/api/python/technical-documentation/) for easy integration
  - **Very affordable pricing:**
    - $1.99 for 200 conversions/month
    - $6.99 for 5,000 conversions/month
    - $24.99 for 50,000 conversions/month
  - **Security & compliance:**
    - GDPR compliant
    - Encryption at rest with customer-provided encryption keys
    - Customer controls decryption keys (Grabzit doesn't store them)
  - **Active development:** Regular updates and new features based on social media presence
  - **Responsive support:** Active community support with staff responses typically within a day
  - **Handles complex elements:**
    - Links preserved
    - Tables with styling
    - Lists including deeply nested lists
    - Inline images (base64 encoded, as produced by mammoth)
- **Cons**
  - **No semantic styling:** List items and other elements use "Normal" style instead of semantic Word styles
  - **Classnames not preserved:** CSS classes are lost during conversion (e.g., table column width classes)
  - **Footnotes non-semantic:** Footnotes are not rendered with semantic Word styles
  - **Limited documentation:** Documentation is sparse, which could complicate troubleshooting

## Links

- [Grabzit HTML to DOCX API](https://grabz.it/html-to-word-docx-api/)
- [Grabzit Python Client Documentation](https://grabz.it/api/python/technical-documentation/)
- [Grabzit Trust Center](https://grabz.it/trust/) (Security and compliance information)
