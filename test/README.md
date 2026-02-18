# Instruction on invoking test cases

---

## Environment setup

You will need to install the dependencies specified in the `requirements.txt` of **this current folder** before invoking pytest.

> Packages specified in requirements.txt accross each folders isn't guaranteed to be identical, in order to perform automated testing against the code base you will need to install the one located in folder `test/`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Run the test cases

In order to make `pytest` locate the test cases automatically, it is adviced to invoke command in the project root.

```bash
pytest -v
```
