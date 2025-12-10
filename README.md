![Python Version from PEP 621 TOML](https://img.shields.io/badge/Python-3.13-blue)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Django CI](https://github.com/HHS/simpler-grants-pdf-builder/actions/workflows/django_ci.yml/badge.svg)](https://github.com/HHS/simpler-grants-pdf-builder/actions/workflows/django_ci.yml)

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

This project uses Python >=3.14.

You can find the exact version of python that is being used by referencing the [Dockerfile](https://github.com/HHS/simpler-grants-pdf-builder/blob/main/Dockerfile#L1). If you want to change your Python version, I would recommend [pyenv](https://github.com/pyenv/pyenv).

<details>

<summary>
Changing Python version
</summary>

#### Changing the Python version

Note: this is not required for initial installation + booting up the app, but I am putting it here so that I remember.

The assumption here is that we are using `pyenv` to manage our Python version.

```bash
# check for currently supported versions of Python
pyenv install --list

# if the version you want is not shown, you can try updating pyenv
brew update && brew upgrade pyenv

# install new version of python with pyenv
pyenv install 3.14.0

# update python versions in various files
# here is a commit that is representative: #538d753a4d961e4d97c783bb7d4157a655ffd12a

# point poetry at the new python
poetry env use 3.14

# refresh lockfile metadata for the new python *without* bumping any packages
poetry lock --no-update

# install exactly from the lockfile
poetry install --sync
```

</details>

### [Install `poetry`](https://python-poetry.org/docs/)

`poetry` is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.

<details>

<summary>
Updating dependencies
</summary>

#### Updating poetry dependencies

Note: this is also not required for initial installation + booting up the app.

```bash
# check for outdated deps
poetry show --outdated

# update 1 package
poetry update django

# reinstall deps from lockfile
poetry install --no-root

# update everything
poetry update

# update only nested dependencies
poetry update --lock

# inspect dependency tree for 1 dependency
poetry show --tree martor
```

</details>

### [Install `pre-commit` hooks](https://pre-commit.com/)

`pre-commit` is a framework for managing and maintaining multi-language pre-commit hooks. It helps ensure code quality by running automated checks before each commit. The dependency is included as a poetry dev dependency, so the only local action is to install the pre-commit hooks for this project:

```bash
# Install the git hook scripts
poetry run pre-commit install

# Optional: run against all files (not just staged changes)
poetry run pre-commit run --all-files
```

Our pre-commit configuration includes:

- **Black**: Python code formatter
- **isort**: Import sorter
- **Django check**: Runs Django's system checks
- **General hooks**: Trailing whitespace, file endings, YAML validation, etc.

The hooks will automatically run on every commit. Files are excluded from formatting if they're in:

- Static files (`nofos/bloom_nofos/static/`)
- Migration files (`*/migrations/`)
- SVG files (`.svg`)
- Certificate files (`.crt`)

### [Install `docker`](https://docs.docker.com/install/)

A docker container allows a developer to package up an application and all of its parts. This means we can build an app in any language, in any stack, and then run it anywhere — whether locally or on a server.

## Create a .env file

You will need a `.env` file to run this application.

```bash
# create .env file from example file
cp ./nofos/bloom_nofos/.env.example ./nofos/bloom_nofos/.env
```

If you are running locally, the example file will work just fine.

## Build and run locally with poetry

Just install the dependencies and boot it up. Pretty slick. 😎

Important: make sure to run poetry commands from the `./nofos` directory.

```bash
# install dependencies
poetry install


# make sure you are in the "./nofos" directory
cd ./nofos

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

Important: make sure to run poetry commands from the `./nofos` directory.

```bash
# running default django commands
poetry run python manage.py {runserver, makemigrations, migrate, etc}
```

## A note on our implementation of the US Web Design System (USWDS)

This app uses a static version of the [US Web Design System (USWDS)](https://designsystem.digital.gov) styles, downloaded on August 11, 2025. At the time of writing, we are using version 3.13.0.

<details>

<summary>
Updating USWDS
</summary>

#### Why we use a static version of USWDS

We don't have a frontend build pipeline, so we don't really fit into the model that USWDS describe for getting up and running [in their tutorial](https://designsystem.digital.gov/documentation/getting-started-for-developers/).

Instead, we link to USWDS built assets in our `<head>` that we serve from our static folder.

Periodically, we refresh these files with the newer versions so that we bring in the most recent updates.

#### Steps to update USWDS

1. Visit downloads page: https://designsystem.digital.gov/download/
2. "Download code"
3. Copy static assets to Django /static/uswds folder
   1. Copy `/dist/css/uswds.css`
   2. Copy `/dist/js/uswds-init.js`
   3. Copy `/dist/js/uswds.js`
   4. Move them all into `/nofos/bloom_nofos/static/uswds`
4. Inside of "uswds.css", do a find-replace:
   1. Find/replace: "../fonts" to `/static/fonts`
   2. Find/replace: "../img" to `/static/img`
5. Copy in new images
   1. Copy all images in `dist/img/` (not subfolders)
   2. Move them to `/nofos/bloom_nofos/static/img`
6. Done!

#### Done?

Well, yes and no. Technically, this is all you need to do, but we don't know if the new version of USWDS creates any layout issues for us. The actual diffs of what changed since the last version of USWDS is too large to meaningfully understand, so we have to do this manaully.

The last step is looking through the app vs a deployed version and checking for differences in layout.

If found, you can decide if the new change is better/equivalent. If not then add CSS to revert the change.

</details>

## Environment variables

No additional environment variables are needed to run the application in dev mode, but to run in production, several are needed.

To manually deploy to production, create a new file `./nofos/bloom_nofos/.env.production`.

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

- `DOCRAPTOR_IPS`: IP addresses that we expect DocRaptor requests to come from. Note that these can be overridden.

  - default `""`: this means zero IPs are safelisted

- `API_TOKEN`: Bearer token to allow API access.

  - default `""`: this will block any and all API access.

- `LOGIN_GOV_CLIENT_ID`: Should match the "Issuer" string of our Login.gov app.

  - default `""`: No issuer, will not connect to Login.gov

- `LOGIN_GOV_OIDC_URL`=This is the root URL for Login.gov, where we send our auth requests.

  - default `""`: No url, will not connect to Login.gov

- `LOGIN_GOV_REDIRECT_URI`: The URL that Login.gov will redirect to after authentication.

  - default `""`: No url, will not connect to Login.gov

- `GOOGLE_CLOUD_PROJECT`: the GCP project ID containing our Login.gov `.pem` file.

  - default `""`: No project ID, will try to use [local cert files](https://github.com/HHS/simpler-grants-pdf-builder?tab=readme-ov-file#option-1-using-local-certificate-files)

## Login.gov Key Configuration

This application uses Login.gov for authentication and requires both private and
public keys. These keys can be sourced from either Google Cloud Secret Manager
or local files.

If you do not have these cert files, you won’t be able to log in with Login.gov, but
you will still be able to login with Django Auth.

### Development Environment

For local development, the application will:

1. Attempt to fetch keys from Google Cloud Secret Manager if `GOOGLE_CLOUD_PROJECT` env is set.
2. If `GOOGLE_CLOUD_PROJECT` is missing or Secret Manager access fails, fall back to local certificate files.

#### Option 1: Using Local Certificate Files

1. Place your Login.gov certificate files in `./nofos/bloom_nofos/certs/`:

   - `login-gov-private.pem`
   - `login-gov-public.crt`

2. No additional configuration needed - the application will automatically use
   these files if Secret Manager access fails

#### Option 2: Using Google Cloud Secret Manager

1. Ensure you have access to the `bloom-nofos-1` project in Google Cloud
2. You need the "Secret Manager Secret Accessor" role
   (`roles/secretmanager.secretAccessor`)
   - This can be granted by a project admin
   - Even if you have the Editor role, you still need this specific role for
     secret access
3. Configure your environment:
   ```bash
   # Set up Google Cloud authentication
   gcloud auth application-default login
   gcloud config set project bloom-nofos-1
   gcloud auth application-default set-quota-project bloom-nofos-1
   ```
4. This will fetch the private key for you to use, the public keys should be commited to the ./nofos/bloom_nofos/certs directory

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
