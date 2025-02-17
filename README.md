<div align="center">
  <h1>NOFO Builder</h1>
  <h3>📄<sup>✍️</sup>🦆</h1>
  <p><em>The no-code NOFO web flow</em></p>
</div>

## About

The NOFO Builder is a Word-2-PDF pipeline that ingests Word files and generates a tagged PDF file using a USWDS-based design that is both accessible and attractive for applicants. It is a tool to build publishable PDFs from reviewed and finalized NOFO documents.

The NOFO Builder is a Django app that can be run as a Python process or as a Docker container.

## What is a NOFO?

A "Notice of Financial Opportunity" (NOFO) is a big document accouncing government funding for certain projects or activities (like an <abbr title="request for proposal">RFP</abbr>). Suppliers can bid on the NOFO for a chance to win funding for delivering the specified outcome.

An example of a NOFO might be an announcement of funding to provide preschool services in Florida.

NOFOs are typically very long, very plain documents without much in the way of formatting.

The SimplerNOFOs project relies on NOFOs that have been written using content guides: essentially, templated starter documents that ensure NOFOs are structured in similar ways.

Once the NOFO documents have been finalized, the NOFO Builder imports these documents as .docx files to generate publishable PDFs that are better structured and easier to read.

## Workflow

NOFOs are written by HHS’ Operating Divisions (OpDivs), and peer-edited by Bloom editing coaches, before proceeding through internal reviews. The writing and editing happens using ‘content guides:’ template-like Word documents that provide a starting point for new NOFOs. Content guides use tagged headings, lists, and tables, and structure the flow of content for a NOFO.

Once a NOFO is reviewed and approved, our workflow is:

1. NOFO is approved to be published
2. A NOFO designer receives the finalized .docx file
3. The NOFO designer logs into the NOFO builder
4. The NOFO designer uploads the .docx file to create an HTML representation of the NOFO
5. The NOFO designer can view and make edits to the uploaded NOFO
6. We use a PDF renderer to output the NOFO as a PDF, based on the HTML layout.
7. Done!

## Getting started

### [Install `python`](https://www.python.org)

`python` is a high-level, general-purpose programming language, popular for programming web applications.

This project uses Python >=3.11.

You can find the exact version of python that is being used by referencing the [Dockerfile](https://github.com/HHS/simpler-grants-pdf-builder/blob/main/Dockerfile#L1). If you want to change your Python version, I would recommend [pyenv](https://github.com/pyenv/pyenv).

### [Install `poetry`](https://python-poetry.org/docs/)

`poetry` is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.

### [Install `docker`](https://docs.docker.com/install/)

A docker container allows a developer to package up an application and all of its parts. This means we can build an app in any language, in any stack, and then run it anywhere — whether locally or on a server.

## Create a .env file

You will need a `.env` file to run this application.

```bash
# create .env file from example file
cp ./bloom_nofos/bloom_nofos/.env.example ./bloom_nofos/bloom_nofos/.env
```

If you are running locally, the example file will work just fine.

## Build and run locally with poetry

Just install the dependencies and boot it up. Pretty slick. 😎

Important: make sure to run poetry commands from the `./bloom_nofos` directory.

```bash
# install dependencies
poetry install

# make sure you are in the "./bloom_nofos" directory
cd ./bloom_nofos

# run migrations (needed when first booting up the app)
poetry run migrate

# run application in 'dev' mode
# (ie, the server restarts when you save a file)
poetry run start
```

The app should be running at [http://localhost:8000/](http://localhost:8000/).

On a Mac, press `Control` + `C` to quit the running application.

### Adding users

Currently, the NOFO Builder is an internal tool whose entire purpose is managing and printing NOFO documents, so the user features are pretty barebones. What this means is that we rely on the Django admin for user adminstration.

During first-time setup, create a superuser account.

```bash
# create superuser account
poetry run python manage.py createsuperuser
```

Superusers are the only accounts able to access the admin backend at [http://localhost:8000/admin](http://localhost:8000/admin). Once you are logged in, you can use the admin backend to create and manage accounts for new users.

### Running default django commands with poetry

Django's default commands can be run by calling `python manage.py {command}`. In this repo, we are using poetry to run them.

Important: make sure to run poetry commands from the `./bloom_nofos` directory.

```bash
# running default django commands
poetry run python manage.py {runserver, makemigrations, migrate, etc}
```

## A note on the CSS/HTML

This app uses a static version of the [US Web Design System (USWDS)](https://designsystem.digital.gov) styles, generated on November 8th, 2023.

I've made a couple of tweaks so that they work in this app.

### Adjustments to styles.css

- Update font paths from "../fonts" to "/static/fonts"
- Update icon paths from "../img/usa-icons" to "/static/img/usa-icons"
- Update img paths from "../img" to "/static/img"

## Environment variables

No additional environment variables are needed to run the application in dev mode, but to run in production, several are needed.

To manually deploy to production, create a new file `./bloom_nofos/bloom_nofos/.env.production`.

- `DEBUG=false`: Never run in production with debug mode turned on.

  - default `True`

- `SECRET_KEY`: used by Django to encrypt sessions. This can be any random string of sufficient complexity.

  - default `secret-key-123`

- `DATABASE_URL`: This app can be configured to use an external database or a local SQLite database. In production, it uses an external Postgres database.

  - default `""`: this means Django will default to using a local SQLite database.

- `DJANGO_ALLOWED_HOSTS`: Django will not run correctly on the server unless the domain is specified ahead of time. This env var can contain 1 domain or a comma-separated list of domains

  - default `""`: no effect unless Django is running in production.

- `DOCRAPTOR_API_KEY`: Our API key for printing documents using DocRaptor.

  - default `"YOUR_API_KEY_HERE"`: this key works for printing test documents (with a watermark)

  - default `""`: this means zero IPs are safelisted

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
