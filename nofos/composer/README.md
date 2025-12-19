# NOFO Composer MVP — Product Documentation

This page documents how the NOFO Composer MVP was researched, designed, built, and evaluated. It is intended to support long-term ownership, maintenance, and iteration by any product, design, and engineering teams.

## Overview

**NOFO Composer** is part of the Simpler NOFOs initiative and supports HHS staff in creating, managing, and using standardized NOFO content guides. The MVP focuses on:

- A guided, in-browser experience for **NOFO Writers** to generate customized content guides
- A management experience for **System Administrators** to configure and validate content guides
- Establishing a foundation for future releases, including Word export, OpDiv Admin roles, and governance features
  This documentation captures:
- The _why_ (user needs and policy context)
- The _what_ (MVP scope and product decisions)
- The _how_ (design patterns, architecture, and implementation notes)

Composer is intentionally positioned as a **starting point for authoring**, not a replacement for downstream drafting or review tools.

---

## Product Goals and MVP Scope

### Goals

- Reduce confusion and manual effort in NOFO drafting
- Increase confidence that content guides are accurate and up to date
- Improve NOFO standardization while preserving necessary OpDiv flexibility
- Lay the groundwork for scalable governance and future enhancements

### In Scope for MVP

- Writer flow to generate a customized content guide through a guided setup
- System Admin flow to manage and validate content guides
- Previewing generated content guides
- In-browser experience only (no Word export in MVP)

### Out of Scope for MVP

- OpDiv Admin role (validated indirectly through System Admin testing)
- Track changes, commenting, or messaging
- Word export (planned for next release)

---

## Using Composer

Follow the startup steps to get the app running [in the main README.md](https://github.com/HHS/simpler-grants-pdf-builder/blob/main/README.md#build-and-run-locally-with-poetry).

Once it is running, you can visit the System Admin dashboard at:

- [http://localhost:8000/composer/](http://localhost:8000/composer/)

Here you can build your content guide by importing an existing content guide.

Once it is ready, you can publish it and visit the NOFO writer dashboard at:

- [http://localhost:8000/composer/writer/](http://localhost:8000/composer/writer/)

You can "start a draft NOFO", pick your newly published draft NOFO and then you can get started editing the various sections in it.

## User Roles

1. **System Administrators (HHS Office of Grants)**
   Act as superusers who manage content guides and validate core Policy Admin functionality.

2. **NOFO Writers**
   Generate customized content guides and use them as a starting point for drafting.

_Note: The OpDiv Admin/Policy Admin role (bureau directors, lead authors, agency policy leadership, etc.) was explored and validated through research and user acceptance testing but not implemented for this MVP._

---

## Research Foundations

### Research Framing

Research examined governance needs and authoring workflows together, with the understanding that:

- **Policy governance establishes the foundation**
- **Writer workflows build on that foundation**
- Adoption depends on trust, clarity, and workflow fit — not feature completeness

Composer MVP was evaluated as a **validated starting point**, not an end-to-end authoring solution.

### Methods

- Foundational interviews with HHS Office of Grants stakeholders
- Participatory interviews with Policy Admins and NOFO writers
- Concept evaluation using a clickable prototype
- Task-based usability and acceptance testing with Writers and HHS Admins

### Key Insights

- Centralized governance and visibility into changes are prerequisites for scale
- Writers need Composer to reflect real-world drafting stages, not a single-pass flow
- Word remains the system of record for drafting, collaboration, and clearance
- Clear cues about locking, permissions, and system behavior are critical to trust

---

## Design Approach

### Design Principles

Composer MVP design prioritized:

- **Governance-first design**
- **Progressive disclosure of complexity**
- **Familiar structure aligned to content guides**
- **Clarity about constraints, roles, and system behavior**

### MVP Scope Decisions

The MVP intentionally:

- Focuses on Writer and HHS Admin experiences
- Validates governance, permissions, and structured content behavior
- Excludes full OpDiv Policy Admin tooling
- Does not include Word export (approved and in progress as a fast follow)

These constraints were intentional to validate foundational assumptions before scaling.

---

## Engineering Overview

The Composer is a two-sided product:

- System Admin users create Content Guides
- NOFO Writer users create Content Guide Instances, which are based on a given Content Guide

### ContentGuides and ContentGuideInstances

Both the ContentGuide and ContentGuideInstance follow the same overall structure as a NOFO object. (See [nofos/composer/models.py](https://github.com/HHS/simpler-grants-pdf-builder/blob/main/nofos/composer/models.py))

At a high level, we have a document. That document has one or more sections, and each section has one or more subsections.

```
ContentGuide -> has 1 or more -> ContentGuideSection -> has 1 or more -> ContentGuideSubsection

ContentGuideInstance -> has 1 or more -> ContentGuideSection -> has 1 or more -> ContentGuideSubsection
```

#### Differences between ContentGuide\* models and regular NOFO models

Documents:

- A ContentGuide has only 2 statuses: draft and published
- A ContentGuideInstance has a parent ContentGuide
- A ContentGuideInstance has a “conditional_questions” k-v store which we use to filter the right subsections when populating this instance from the original ContentGuide.

Sections:

- A ContentGuideSection can have _either_ a parent ContentGuide or ContentGuideInstance, not both

Subsections:

- A ContentGuideSubsection has instructions (these are never a part of NOFO Subsections)
- A ContentGuideSubsection has an “edit mode” which defines how this subsection can be edited by a NOFO Writer.
- A ContentGuideSubsection _can_ have “variables”, which are a list of variables in the body text formatted between curly braces (e.g., `{This is a variable.}`). NOFO Writers will be asked to enter a string value for each variable. A subsection can only have variables if the edit_mode is “variables”.
- A ContentGuideSubsection can be optional, which lets NOFO Writers show or hide the section.
- A ContentGuideSubsection knows if it is affected by a conditional question, and can tell you if it should appear based on a “Yes” or “No” answer from a Writer.

#### Publishing and unpublishing

ContentGuideInstances must be created from a parent ContentGuide, which serves as the template for that instance.

However, we allow System Admins to unpublish their ContentGuides in order to make changes to them and then re-publish them. This means that you could up in a situation where an instance is ‘based on’ a content guide that no longer matches it.

In order to avoid this scenario, we create a cloned, archived Content Guide whenever one is unpublished. The cloned ContentGuide is re-assigned as the parent of the ContentGuideInstance, because it matches the template that the writer started with. The original ContentGuide is also marked as the ‘successor’ to the cloned guide. So, from a ContentGuideInstance, you can always find a link to a matching ContentGuide, and a cloned ContentGuide always can link you to its updated guide.

This is all invisible to the user. It is possible to find the original ContentGuide through a ContentGuideInstance, but we don’t expose this to NOFO Writers currently.

### User types

ContentGuides can only be created by superadmins (Bloom users) or by users with the `is_staff` attribute. Previously, we didn’t use the `is_staff` attribute for anything.

NOFO Writers are not expected to have the `is_staff`. A non-staff user can see published ContentGuides but cannot see draft content guides.

All users have the ability to create ContentGuideInstances, which we call “draft NOFOs” in the UI. We don’t anticipate that System Admin users will be creating draft NOFOs but there didn’t seem to be any reason to prevent it.

---

## Validation and Outcomes

### Success Criteria

Composer MVP met its Quad 4 (ending on January 6, 2026) success criteria for:

- Ease of use
- Workflow improvement
- Adoption readiness
- Validation of core governance behaviors

### What This Means

Composer MVP is a **validated starting point**, but **not ready for launch**.

Results indicate readiness for fast-follow iterations focused on:

- Governance clarity
- Clear transitions between Composer and existing drafting, review, and collaboration workflows
- Flexibility to support existing drafting and review workflows, including Word import and export

---

## Gaps and Future Work

### ⏱️ Now: Establish governance and workflow foundations

- Deliver reliable Word export as a core workflow bridge
- Establish a three-tier role model (HHS Admin, OpDiv Policy Admin, Writer)
- Implement multi-level locking and approvals
- Provide clear system cues explaining what is locked, why, and by whom
- Introduce version history and restore capabilities

### ➡️ Next: Improve workflow transitions and drafting confidence

- Clarify when and how to move work into Word
- Align save, preview, and exit behaviors with drafting expectations
- Support deferred setup decisions
- Enable sharing drafts for offline review

### 🔮 Later: Converge tools and scale

- Fold NOFO Compare into the core authoring experience
- Explore safe pathways to re-import approved content
- Consolidate Composer and NOFO Builder once export/import is reliable

---

## Linked Artifacts

- [Composer MVP Research Report](https://gartner365.sharepoint.com/:p:/r/sites/HHS947/Shared%20Documents/General/%5BINTERNAL%5D%20Bloom%20Works/NOFO%20Composer/Quad%204%20Agile%20Deliverable%20-%20Deliver%20the%20NOFO%20Composer%20MVP/04%20Findings/NOFO%20Composer%20MVP%20Research%20Report.pptx?d=wc89205ed36d14993803a4d54dcf67c14&csf=1&web=1&e=SLnKd3)
- [Figma HHS Admin Prototype](https://www.figma.com/proto/J41kYT5DvfnxYgqzaB6FKP/NOFO-Composer?page-id=98%3A4490&node-id=1265-15979&viewport=951%2C-975%2C0.08&t=Z2nXEH5Cynl955z2-8&scaling=min-zoom&content-scaling=fixed&starting-point-node-id=1265%3A15979&hide-ui=1)
- Figma Writer Prototype
- [Composer MVP overview demo video](https://gartner365.sharepoint.com/:v:/r/sites/HHS947/Shared%20Documents/General/%5BINTERNAL%5D%20Bloom%20Works/NOFO%20Composer/Quad%204%20Agile%20Deliverable%20-%20Deliver%20the%20NOFO%20Composer%20MVP/04%20Findings/Composer-MVP-visual-overview.mov?csf=1&web=1&e=7taIz0)

---

## Known Limitations and Risks

- Variables are as simple as we could feasibly make them, and are not prime-time

- All variables have to be a string, and we currently don’t support anything other than a textarea. In testing people expected other formats (numbers or dollar sign inputs) as well as pointing out some input variables would be better suited as lists, textareas, or select boxes.

- 2 user types is not enough for the Composer. We currently have “System Admins” who can fully create and edit all parts of a content guide, and writers who are constrained in what they can input. However, we discussed an in-between user type, a Policy Admin, who would have delegated editing permissions granted by a System Admin. This kind of role seems necessary, as it would come up often in our research.

- Using a markdown editor is not a good choice for a general user. Very few administrative staff understand markdown and all expect a Word document. However, we know that most content is drafted in Word and copied in to our system, generally.

- In order of importance, it is strongly recommended to support:
  - import from a Word document (this is working)
  - preserve formatting and elements from Word when pasting in (e.g., lists, tables) (this is not working)
  - swap the markdown editor for a rich text editor.

---

## Ownership and Handoff Notes

This repository contains:

- Research context explaining _why_ Composer exists
- Design artifacts explaining _how_ users interact with it
- Engineering documentation explaining _how_ it is built
  A new team should be able to:

1. Understand user needs and constraints without re-running discovery
2. Identify which MVP decisions were validated vs deferred
3. Extend Composer without breaking core assumptions
   For questions or historical context, see

- `docs/
- `docs/
