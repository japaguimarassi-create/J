# Small-scale training and inference demonstration

This report records a genuine end-to-end smoke test of the project-owned pipeline. The corpus is original demonstration text in data/demo_corpus.txt and is released under CC0 1.0 in data/LICENSE.md.

| Property | Observed result |
|---|---:|
| Training updates | 60 |
| Trainable parameters | 86,720 |
| Tokenizer vocabulary | 320 IDs |
| Context length | 48 tokens |
| Model width | 64 |
| Attention heads | 4 |
| Transformer blocks | 2 |
| Feed-forward width | 128 |
| Device | CPU |
| Training loss at step 60 | 4.345345 |
| Validation loss at step 60 | 4.4094242 |
| Runtime checkpoint load | Passed |
| Autoregressive generation | Passed |

The local run used Python 3.13.5 and PyTorch 2.10.0+cpu. The repository dependency pins PyTorch 2.14.1, so this is not evidence for that exact wheel.

Prompt: Klod é um projeto

Generated continuation: dee m die dciso veridsidvs ltcoa is

The output is incoherent. This run proves only that tokenization, backpropagation, optimizer updates, validation, checkpoint serialization/loading and autoregressive inference execute. It does not prove language competence.

The binary checkpoint stays in the ignored local artifacts directory and is not committed. The training recipe is included in README.
