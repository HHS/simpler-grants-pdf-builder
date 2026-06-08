# Groups

## Overview

Both NOFOs and users have a `group` field, which controls who can see them and what they can see.

The `group` field is an enum — not a free text field. All group values are predefined in `nofos/bloom_nofos/settings.py` under `GROUP_CHOICES`. Selecting a group means picking from a list of known options.

Users of a specific group can see all NOFOs assigned to that group, but cannot see NOFOs from any other group.

The one exception is the Bloom group, whose users can see all NOFOs across all groups. The NOFO list on the index page defaults to Bloom NOFOs for Bloom users.

## User roles and group permissions

There are three user roles: standard User, OpDiv Admin, and Superuser.

**OpDiv Admin** users have user management capabilities within their group. They can:

- View all users in their group
- Create new users in their group
- Delete unused accounts in their group
- Reset passwords for users in their group
- Add or remove OpDiv Admin status for other users in their group

OpDiv Admins have the same NOFO visibility as other users in their group — they can only ever see NOFOs assigned to their group.

**Superuser** status grants full administrative access across the application. Superuser status may only be assigned to users in the Bloom group.

## How group is assigned

### Users

A user's group is set when the user is created. The group can be changed later, but only by a superuser. OpDiv Admin users cannot see or change their own group, or the group of other users.

### NOFOs

A NOFO's group is assigned based on the user who imported it. For example, if an HRSA user imports a NOFO document, it becomes an HRSA NOFO and is visible to all other HRSA users (and Bloom users).

Bloom users can reassign the group of a NOFO — for example, to share it with an OpDiv user.

## Adding a new group

Adding a new group requires a code change. Follow these steps:

### 1. Add the group value to `settings.py`

Group values are defined in `nofos/bloom_nofos/settings.py` under `GROUP_CHOICES`. Each entry includes a slug and a display name. For example:

```python
("hrsa", "HRSA: Health Resources and Services Administration")
```

The slug is used for code comparisons and CSS class names. The display name is shown in the UI.

### 2. Generate migration files

From the `./nofos` directory, run:

```bash
poetry run python manage.py makemigrations
```

`group` is an enum field on multiple models. Adding a new group value updates the permitted values on all of them:

- `users.BloomUser`
- `nofos.Nofo`
- `compare.CompareDocument`
- `composer.ContentGuide`
- `composer.ContentGuideInstance`

Review the generated migration files before applying them.

### 3. Apply the migrations

```bash
poetry run python manage.py migrate
```

### 4. Add a theme color and CSS class to `shared.css`

Each group has a theme color used to visually tag users and NOFOs in the UI. Add a new CSS variable at the top of `nofos/bloom_nofos/static/shared.css`, then add a corresponding class using the group's slug.

For example, for a group with slug `"acf"`:

```css
--color--acf-blue: #your-color-here;
```

```css
.bg-group--acf {
  background-color: var(--color--acf-blue);
}
```

For a reference example, see [PR #698 — Adding NIH as a new group](https://github.com/HHS/simpler-grants-pdf-builder/pull/698).
