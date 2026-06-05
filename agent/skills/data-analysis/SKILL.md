---
name: data-analysis
description: Explore and analyze a dataset (CSV/JSON) with pandas, then summarize findings.
---

# Data analysis skill

Follow this loop when asked to analyze a dataset:

1. **Locate the data.** Use `list_files` to find the dataset in the workspace.
   If the user named a file, confirm it exists with `read_file` (peek at the
   first lines) before loading the whole thing.

2. **Load and inspect.** With `run_python`, load it into pandas and print the
   essentials first; never assume the schema:
   ```python
   import pandas as pd
   df = pd.read_csv("data.csv")
   print(df.shape)
   print(df.dtypes)
   print(df.head())
   print(df.describe(include="all"))
   ```

3. **Answer the question.** Compute exactly what was asked. Print intermediate
   results so you can see and verify them. One focused computation per step.

4. **Handle the messy reality.** Check for nulls, wrong dtypes, and duplicates
   before trusting an aggregate. If a column is dirty, clean it explicitly and
   say what you did.

5. **Summarize for a human.** End with a short plain-language summary of the
   findings: numbers in context, not raw dataframes.

If a `run_python` snippet fails with `ModuleNotFoundError` (e.g. pandas isn't
in the sandbox), call `install_packages` with the missing package(s), like
`["pandas"]`, then re-run your code. Do this proactively for pandas before
your first analysis step.
