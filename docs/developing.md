# Mopeka-Pro-Check - Developing

## Setup

1. Clone the repo
2. Install the repo (virtual environments are strongly encouraged)

    ``` bash
    pip install --upgrade -e .
    ```

3. Install dev requirements

    ``` bash
    pip install --upgrade -r requirements.txt
    ```

## CI / Pre-Commit Process

Should run black
Should run example
Should author unit tests, confirm coverage, and passing result

### Run unit tests

Python built in UnitTest library is supported as well as pytest.  Then use pytest to run
and make report as well as provide coverage information.  

pytest -v --html=pytest_report.html --self-contained-html --cov=mopeka_pro_check --cov-report html:cov_html

## Publish new version to pypi

1. Commit version and tag it in git vXX.YY.ZZ  (XX == Major, YY: minor, ZZ: patch)
2. Build wheel

    ``` bash
    python setup.py sdist bdist_wheel
    ```

3. Publish to Pypi

    ``` bash
    python -m twine upload dist/*
    ```
