# Admin styling

Django supplies admin CSS, JavaScript, images, and vendor assets through
`django.contrib.admin`. Keep these assets paired with the installed Django
version: do not copy collected `admin/` files into
`nofos/bloom_nofos/static/`. Project static directories take precedence over
Django's files, so copied assets can break new admin markup after upgrades.

The old project `static/admin/` directory was an unchanged copy of Django
4.2.7's assets. Removing it lets staticfiles and `collectstatic` select assets
from the installed Django package automatically, including accessibility,
responsive layout, and widget updates.

For project customizations, extend `admin/base_site.html` and load a small,
separately named stylesheet through a block that preserves `block.super`.
The existing Constance table wrapping adjustment lives in that template.

After upgrading Django, check admin login, breadcrumbs, sidebar, change lists,
change forms, and widgets in light and dark modes and at narrow widths. Run
`python manage.py test bloom_nofos.tests_bloom_nofos.test_admin_assets` from
`nofos/` to check that staticfiles still resolves admin assets to Django.
Deployment must run `collectstatic` so the installed assets reach the server.
