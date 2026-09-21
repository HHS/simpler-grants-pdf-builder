# OpDiv NOFO search access

Captured September 21, 2026 in local Chrome at 1374 × 1035 using the running
Django application and synthetic records. The signed-in account is a regular
CDC user: it is neither a superuser nor an OpDiv admin.

- [Before](before.png): opening Search NOFOs returns `Permission denied`.
- [After](after.png): the same user can search successfully and sees the matching
  CDC NOFO.

The fixture also includes a matching HRSA NOFO. Its absence from the after
screenshot verifies that results are limited to the signed-in user's OpDiv
group. Automated tests separately cover CDC and HRSA users searching their own
groups, cross-group isolation, `bloom` users' broader visibility, and anonymous
users being redirected to login.
