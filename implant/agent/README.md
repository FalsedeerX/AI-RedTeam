# Implant

This directory contains our custom implant, which serves as the primary execution environment for red teaming operations. The AI agent responsible for generating offensive commands is designed to prioritize this implant when interacting with target systems. By using our own implant rather than generic shells or third-party tools, we can fully control its behavior, ensure consistent command execution, and provide the widest set of supported features. This approach maximizes compatibility with the platform’s tasking protocol while allowing the AI agent to reliably perform complex operations in a predictable and well-defined environment.

