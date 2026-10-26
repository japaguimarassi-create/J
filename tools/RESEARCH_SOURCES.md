# Research sources and training method

Reviewed for the Reality Engine AI Minecraft 1.7.10 classifier and Forge implementation:

- Forge 1.7.10 / 10.13.4.1614 Javadocs: https://skmedix.github.io/ForgeJavaDocs/javadoc/forge/1.7.10-10.13.4.1614/
- Hugging Face Transformers Trainer documentation: https://huggingface.co/docs/transformers/en/main_classes/trainer
- Hugging Face model cards: https://huggingface.co/docs/hub/en/model-cards
- scikit-learn model evaluation: https://scikit-learn.org/stable/modules/model_evaluation.html
- Intent classification evaluation dataset paper: https://aclanthology.org/D19-1131/

The model training corpus is project-specific and curated in tools/train_brain.py. The distinct base prompts are split into training, validation and held-out test sets before augmentation. The generated report includes split sizes, optimizer settings, held-out accuracy, macro-F1, per-class F1, confusion matrix, early-stopping reason and number of generations actually executed.

A lower training loss is not the same as better generalization. Internet search is a sourced retrieval feature, not an automatic untrusted-data-to-executable-code pipeline. This compact model is a specialized intent classifier, not a general-purpose large language model.
