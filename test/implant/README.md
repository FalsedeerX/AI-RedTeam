Here is a **shorter and cleaner version**:

---

# Implant Prototype

This directory contains **stripped-down prototype code** used to verify the implant communication protocol.

The current files include a minimal Flask server and simple test clients to validate the basic workflow, such as:

* implant **beacon / registration** (`/beacon`)
* command **result reporting** (`/report`)

The purpose of this prototype is to ensure the **protocol and data flow work as expected** before integrating the full implant implementation.

## Testing

Only basic protocol behavior is verified automatically.
Some future features (e.g., file browsing or interactive shell streaming) require persistent or interactive sessions and are **not suitable for CI/CD testing**, so they will be **verified manually during development**.

## Note

These files are **temporary testing components** and do not represent the final implant architecture.

