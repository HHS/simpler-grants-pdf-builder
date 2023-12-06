<div align="center">
  <h1>NOFO Builder</h1>
  <h3>📄<sup>✍️</sup>🦆</h1>
  <p><em>The no-code NOFO web flow</em></p>
</div>

## About

The NOFO Builder is a Word-2-PDF pipeline that injests HTML files and generates a tagged PDF file using a USWDS-based design that is both accessible and attractive for applicants.

The NOFO Builder is an internal tool for NOFO coaches to use to build publishable PDFs from reviewed and finalized NOFO documents.

The NOFO BUilder is a Django app that can be run as a Python process or as a Docker container.

## What is a NOFO?

A "Notice of Financial Opportunity" (NOFO) is a big document accouncing government funding for certain projects or activities (like an <abbr title="request for proposal">RFP</abbr>). Suppliers can bid on the NOFO for a chance to win funding for delivering the specified outcome.

An example of a NOFO might be an announcement of funding to provide preschool services in Florida.

NOFOs are typically very long, very plain documents without much in the way of formatting. The NOFO Builder uses a new design to generate NOFOs that are better structured and easier to read.

## Workflow

NOFOs are written by HHS’ Operating Divisions (OpDivs), and peer-edited by Bloom editing coaches, before proceeding through internal reviews. The writing and editing happens in specific Word documents that provide a starting point in terms of NOFO structure (‘content guides’). Content guides use tagged headings, lists, and tables, to structure the NOFO.

Once a NOFO is reviewed and approved, our anticipated workflow is:

1. NOFO is approved to be published
2. A Bloom coach exports the Word document as an HTML file
3. The Bloom coach logs into the NOFO builder
4. The Bloom coach uploads the HTML file to create a Markdown representation of the NOFO
   - optional: The Bloom coach can make edits to their uploaded NOFO
5. The NOFO is rendered in HTML
6. We use a PDF renderer to output the NOFO as a PDF, based on the HTML layout.
7. Done!

## Getting started

### [Install `python`](https://www.python.org)

`python` is a high-level, general-purpose programming language, popular for programming web applications.

This project uses Python >=3.10.

### [Install `poetry`](https://www.npmjs.com/get-npm)

`poetry` is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.

### [Install `docker`](https://docs.docker.com/install/)

A docker container allows a developer to package up an application and all of its parts. This means we can build an app in any language, in any stack, and then run it anywhere — whether locally or on a server.

## Build and run locally with poetry

Just install the dependencies and boot it up. Pretty slick. 😎

Important: make sure to run poetry commands from the `./bloom_nofos` directory.

```bash
# install dependencies
poetry install

# run application in 'dev' mode
# (ie, the server restarts when you save a file)
poetry run start
```

The app should be running at [http://localhost:8000/](http://localhost:8000/).

On a Mac, press `Control` + `C` to quit the running application.

### Running default django commands with poetry

Django's default commands can be run by calling `python manage.py {command}`. In this repo, we are using poetry to run them.

Important: make sure to run poetry commands from the `./bloom_nofos` directory.

```bash
# running default django commands
poetry run python manage.py {runserver, makemigrations, migrate, etc}
```

## A note on the CSS

This app uses a static version of the [US Web Design System (USWDS)](https://designsystem.digital.gov) styles, generated on November 8th, 2023.

I've made a couple of tweaks so that they work in this app.

### Adjustments to styles.css

- Update font paths from "../fonts" to "/static/fonts"
- Update icon paths from "../img/usa-icons" to "/static/img/usa-icons"

## Environment variables

No environment variables are needed to run the application in dev mode, but to run in production, several are needed.

To deploy to production, create a new file `./bloom_nofos/bloom_nofos/.env.production`.

- `DEBUG=false`: Never run in production with debug mode turned on.

  - default `True`

- `SECRET_KEY`: used by Django to encrypt sessions. This can be any random string of sufficient complexity.

  - default `secret-key-123`

- `DATABASE_URL`: This app can be configured to use an external database or a local SQLite database. In production, it uses an external Postgres database.

  - default `""`: this means Django will default to using a local SQLite database.

- `DJANGO_ALLOWED_HOSTS`: Django will not run correctly on the server unless the domain is specified ahead of time. This env var can contain 1 domain or a comma-separated list of domains.
  - default `""`: no effect unless Django is running in production.

## Build and run as a Docker container

```sh
# build an image locally
docker build -t pcraig3/bloom-nofos:{TAG} .

# run the container
docker run -it -p 8000:8000 pcraig3/bloom-nofos:{TAG}
```

The container should be running at http://localhost:8000/.

On a Mac, press Control + C to quit the running docker container.

### Push to Cloud Run from an M1 Mac

Building a container on an M1 Mac to deploy on a cloud environment means targeting `amd64` architecture.

```sh

# build the container
- docker buildx build --platform linux/amd64 --build-arg IS_PROD_ARG=1 -t gcr.io/{SERVICE}/{PROJECT}:{TAG} .

# push the container
- docker push gcr.io/{SERVICE}/{PROJECT}:{TAG}

# deploy the container
- gcloud run deploy {SERVICE} \
   --project {PROJECT} \
   --platform managed \
   --region {REGION} \
   --image gcr.io/{SERVICE}/{PROJECT}:{TAG} \
   --add-cloudsql-instances {SERVICE}:{REGION}:{PROJECT} \
   --allow-unauthenticated
```
