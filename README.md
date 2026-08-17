# `bad_examples/` — intentional SonarQube violations

This folder exists **only** to demonstrate the quality gate failing. It is
excluded from `pytest` and is not imported by the framework.

For **Demo Scenario 1 (failure)** you copy `violations.py.template` to
`violations.py`, commit, and watch the pipeline block the deployment.
For **Demo Scenario 2 (success)** you delete `violations.py`, commit again,
and watch it deploy.

Keeping the file as a `.template` by default means the repository is green
at rest — you opt into the failure rather than living with it.
