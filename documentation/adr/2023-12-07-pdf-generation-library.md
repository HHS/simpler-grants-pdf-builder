# PDF generation library

- **Status:** Active
- **Last Modified:** 2023-12-07 <!-- REQUIRED -->
- **Deciders:** Paul Craig<!-- REQUIRED -->

## Context and Problem Statement

The goal of this ADR is to select a PDF generation library to move forward with creating tagged PDF from NOFO documents. There are several strategies for generating PDFs from source documents, but two very common origin formats are Word documents and HTML pages.

## Decision Drivers <!-- RECOMMENDED -->

- Design Fidelity: This is about how easy it is to replicate designs from Figma.
- Accessibility: Tagged PDFs include semantic information about the content (eg, tagged headers, links, tables, etc.). How accessible is the output of this renderer?
- Ease of use: How easy is it to create the input format required to generate the PDF
- Language: As the author of this application, my preferred programming languages are Python and JavaScript, so what language is this PDF renderer?

## Options Tested

- [Prince](https://www.princexml.com/) (via [DocRaptor](https://docraptor.com/))
- [WeasyPrint](https://weasyprint.org/) — Python
- [pdfme](https://pdfme.readthedocs.io/en/latest/) — Python
- [fdpf2](https://py-pdf.github.io/fpdf2/) — Python
- [pdfmake](http://pdfmake.org) — JavaScript
- [pdfme](https://pdfme.com) — JavaScript (same name, but different library)
- [IronPDF](https://ironpdf.com/python/) — Python (sort of)

## Decision Outcome <!-- REQUIRED -->

Chosen option: DocRaptor, which is a SaaS service that uses Prince to generate and return PDFs from HTML documents.

- It produces designs that are very close to the original HTML and is the most robust PDF renderer I came across.
- Its automatic tagging capabilites are generally excellent.
- It is language agnostic because it's an API service that can be called from any application.
- We preferred DocRaptor over downloading and installing a licensed version of Prince because it simplifies our technical stack, [it has enterprise-grade security](https://docraptor.com/security-and-privacy), it's easy to get started with, and the upfront cost is significantly lower.

### [Prince](https://www.princexml.com/) (via [DocRaptor](https://docraptor.com/))

Prince is an HTML to PDF library which renders tagged PDFs from HTML and CSS source documents. Our workflow here involves exporting a Word doc (or Google doc) as HTML and then using Prince to render the output.

We prefer going through DocRaptor in part because it is easier to get started with.

- **Pros**
  - Very high quality layouts
  - Understands most modern CSS (not `grid`, but it does understand `flexbox`)
  - Preserves tags from the original document (headings, tables, etc)
  - Easy to integrate with any application language
  - Free to generate test documents
- **Cons**
  - Not open-source, requires payment

### [Weasyprint](https://weasyprint.org)

Weasyprint is a free, open-source Python library that turns HTML documents into PDFs. It's pretty easy to set up and start using, and it produces pretty good visual designs, but doesn't perserve HTML tags very well.

- **Pros**
  - High quality layouts
    - Includes custom fonts, colours, running headers and footers, etc.
  - Popular Python library, lots of usage
  - Open source, free
- **Cons**
  - Does not understand some modern CSS. For example, it doesn't render flexbox or grid layouts.
  - Doesn't produce tagged (UA) PDF documents. By default it seems to create an `<NonStruct>` elements for every page and lump everything inside of it.
    - Having said that, the autotagging feature in Acrobat Pro seems to do pretty well with Weasyprint-generated PDFs.
    - Also, according to the GitHub issues, it can create UA PDFs, but I wasn't able to replicate this behaviour in Acrobat Pro.
  - Limited support because of its open-source model

### [pdfme](https://pdfme.readthedocs.io/en/latest/)

pdfme is a free, open-source Python library for producing PDF documents "very similar to how you create documents with LaTex".

- **Pros**
  - Quick to get going
  - Documentation is reasonable
  - Open source
- **Cons**
  - Uses a dict-based DSL for configuration that means documents are not easily portable
  - Doesn't include accessibility tags
  - Can't create 2/3rds column page layout
  - Doesn't support custom fonts

### [fdpf2](https://py-pdf.github.io/fpdf2/)

fpdf2 is a library for simple & fast PDF document generation in Python. It is a fork and the successor of PyFPDF.

- **Pros**
  - Pretty quick to get going
  - Documentation is good
  - Open source, free
- **Cons**
  - Nearly everything requires absolutely positioning elements
  - Configuration as Python code (this is bad, docs aren't portable at all)
  - Can't create 2-column page layouts (unless both columns are full of text

### [pdfmake](https://pdfme.readthedocs.io/en/latest/)

Client/server side PDF printing in pure JavaScript.

- **Pros**
  - Open Source and free
  - Playground on the site is helpful to test functionality
  - JSON config for documents
  - Plenty of layout flexibility, doesn't require absolutely positioning elements
- **Cons**
  - [No accessibility tags](https://github.com/bpampuch/pdfmake/issues/942): headers are just visually bigger, not actually tagged sections

### [pdfme](https://pdfme.com)

Free and Open source PDF generator! Open source, developed by the community, and completely free to use under the MIT license!

- **Pros**
  - Open Source and free
  - Playground on the site is helpful to test functionality
  - Takes first prize on [this dev.to article written by the developer](https://dev.to/handdot/generate-a-pdf-in-js-summary-and-comparison-of-libraries-3k0p)
- **Cons**
  - Requires absolutely positioned elements
  - Seems like the idea is to generate receipts, labels, or event tickets
    - [None of the examples](https://pdfme.com/demo) involve long documents with complex layouts

### [IronPDF](https://ironpdf.com/python/) — Python (sort of)

"A Python PDF Library that prioritizes accuracy, ease of use, and speed."

Didn't actually get this one to work. I'm developing on an M2 MacBook Air, and installing the Python library broke because it's actually a C# application behind the scenes and I didn't have the right libraries installed to make that work. I tried installing it a few different ways but then gave up.

## Links

Some links that were helpful in locating options for PDF generating libaries.

- [A full comparison of 6 JS libraries for generating PDFs](https://dev.to/handdot/generate-a-pdf-in-js-summary-and-comparison-of-libraries-3k0p) —  Mar 21, 2022
- [The Python PDF Ecosystem in 2023](https://martinthoma.medium.com/the-python-pdf-ecosystem-in-2023-819141977442) — Mar 23, 2023
- [Dynamically create PDF, r/django](https://www.reddit.com/r/django/comments/14ru2nu/dynamically_create_pdf/) — July 5, 2023
- [Thread: HTML/CSS-to-PDF-engines that Produce Tagged PDFs](https://webaim.org/discussion/mail_thread?thread=9188) — April 1, 2019
