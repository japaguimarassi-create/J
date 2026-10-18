# Continuous refinement: 16,820,000-cycle target

This branch has a resumable trainer at `ai/continuous_refine.py` and a chunked runner at `ai/run_continuous_refine.sh`.

## Verified training state on 2026-10-17

- Requested target: 16,820,000 optimizer-update cycles.
- Latest checkpoint from the local CPU run: global step 13,650.
- The model has 623,232 parameters; this is a small mechanics/comparison model, not the 10-billion-parameter architecture.
- Recoverable baseline was step 2,500; 11,150 updates have since been executed while retaining model weights and optimizer state.
- Latest validation loss was 3.03202. Best rolling average over ten evaluations was 2.96310 around step 6,100.
- Training split has 12,353 tokens; held-out validation split has 10,581 tokens.
- The exact weights from the earlier interrupted 16,820-step run were not saved and are unrecoverable.

## Resume without reinitializing

Extract the attached continuation bundle to a checkout of this branch. Install dependencies, then run:

```bash
python -m pip install -r requirements.txt
bash run_all_cycles.sh 16820000 1000
```

The runner loads `checkpoints/continuous-16820x1000/latest.pt`, which stores model weights, optimizer state and RNG state. The trainer now inherits the saved optimizer learning rate when `--learning-rate` is omitted, avoiding a silent jump to the higher default when resuming. Explicit rate flags can still override it.

## Validation interpretation

Validation improved early, then regressed after approximately step 6,100 while training loss kept falling. The current corpus is too small for meaningful general intelligence training and repeated cycles on it risk further overfitting. The latest checkpoint preserves continuity; the separate best-model checkpoint preserves the best measured point. Improve and expand the rights-cleared training data and held-out evaluations before treating more cycles as progress toward broad reasoning.

This CPU run did not train the 10-billion-parameter model.
