# Playwright Tests

## Setup

To run you'll need to first install the playwright browsers:

```bash
playwright install
```

You'll also need to set the environment variables:

```bash
export BASIC_USER_USERNAME="some_username"
export BASIC_USER_PASSWORD="some_password"
export ADMIN_USER_USERNAME="some_admin_username"
export ADMIN_USER_PASSWORD="some_admin_password"
```

## Running the tests

To run the tests:

```bash
pytest --playwright ENVIRONMENT
```

Where `ENVIRONMENT` is one of `LOCAL` or `PROD`. You can also add the following options:

- `--headed`: Run the tests in headed mode.
- `--slowmo=MILLISECONDS`: Slow down the tests by the specified number of milliseconds.

## Writing tests

To use codegen to generate playwright code use the following command:

```bash
playwright codegen http://localhost:8000
```

This will open a browser and you can interact with the page. Once you're done, you can copy the generated code and paste it into a test. To make the generated code more applicable to your tests, select "Pytest" from the "Target" dropdown in the upper-right corner.
