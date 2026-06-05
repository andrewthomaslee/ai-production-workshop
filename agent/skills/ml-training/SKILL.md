---
name: ml-training
description: Configure, launch, monitor, and debug model training runs.
---

# ML training skill

You help configure, launch, and debug training runs using `start_training` and
`training_status`.

## Launching
1. Confirm the hyperparameters with the user if they were vague: `epochs`,
   `learning_rate`, `batch_size`. Suggest sensible defaults (e.g. lr=0.1).
2. Call `start_training` with a descriptive `name`.
3. Read the returned summary: did it COMPLETE or FAIL?

## Monitoring
- Use `training_status` with the `job_id` to read the per-epoch metrics.
- Report the loss/accuracy trend in plain language: is loss decreasing smoothly,
  plateauing, or diverging?

## Debugging a failed run
A run FAILS when the loss diverges to NaN, almost always a **learning rate that
is too high**. When this happens:
1. State the diagnosis clearly (which epoch it diverged, the offending lr).
2. Propose a fix (lower the learning rate, e.g. halve it) and, if the user
   agrees, launch a corrected run.
3. Compare the two runs' final metrics to confirm the fix worked.

Always close with a short, human-readable verdict: is this model good enough, and
what would you change next?
