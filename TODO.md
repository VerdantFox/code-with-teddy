# Todos

A list of stuff that needs to get done for the project, categorized and roughly in order of importance.

## Bugs

- [x] FIX BUG: When changing pages with HTMX boost, extra CSS + JS isn't loaded (e.g. blog post page code block CSS)
  - The [`head-support` extension](https://htmx.org/extensions/head-support/) should solve this

## Features

- [ ] Add certbot to auto-renew SSL OR use DNS provider's API to grab certs
- [ ] Add resume to "experience" page
- [ ] Add blog comment likes
- [ ] Add projects to projects page (plus individual pages as needed)
  - [ ] Finance (complete first)
  - [x] Twisted towers
  - [x] Connect 4 (remake first)
  - [x] Moth hunt
  - [x] File renamer
  - [ ] Portfolio website (link to blog post about technologies)
  - [ ] Analytics page (remake first) -- maybe sentry can do this?
- [ ] Set up Oauth2 authentication (google and github)
- [ ] Allow users to delete their account
- [ ] Set up email service
  - [x] Emails to me for blog post comments
  - [ ] Emails to other subscribers for blog post comments
  - [x] Emails for recover password
  - [x] Supply domain to whoever so emails don't go to spam
- [ ] Look up extra security desired
  - [x] CSP
  - [x] Replace python-jose dependency
  - [x] Look into code scanning errors
  - [ ] etc.
- [x] Set up logging
  - [x] log to files that clean up automatically
  - [ ] See if other info should be logged
  - [x] Connect with Sentry for logging
- [ ] Make nginx brotli work
- [ ] Make projects searchable
- [ ] Rebuild projects
  - [ ] Finance
  - [x] Connect 4
  - [ ] Analytics
- [ ] New projects
  - [ ] Games API (plus blog post series)
  - [ ] Multiplayer sockets game (plus blog posts)

## Refactors

- [ ] Refactor to separate db models from services models
  - [ ] Add sqlite database option (for faster tests)

## Tests

- [x] Write tests
  - [x] functional tests against FastAPI
  - [x] unit tests for high-value, low-level functions
  - [x] playwright end-to-end tests
  - [ ] Integration tests (maybe)
  - [ ] Locust stress tests
- [x] Set up alembic migrations
  - [x] Initial migration
  - [x] Get alembic working with deploy script
  - [ ] Use alembic in tests

## Done (clear these out when not relevant)

- [x] Index site (add sitemap.xml, robots.txt, etc.)
