# Literature notes — autonomous mechanism research

These notes are hypothesis-directed, not a systematic review. Each item
separates what the source establishes from how it informs this project.

## In-context function learning and algorithmic execution

### Garg et al. (2022), *What Can Transformers Learn In-Context?*

- **Source claim:** transformers trained on synthetic tasks can learn unseen
  linear functions in context and approach least-squares behavior.
- **Our relevance:** rule induction is possible in an appropriate trained model;
  this does not show that DeepSeek V4 Flash infers GF(7) affine rules from the
  current serialization.
- **Source:** https://arxiv.org/abs/2208.01066

### Akyürek et al. (2023), *What Learning Algorithm Is In-Context Learning?*

- **Source claim:** transformer constructions and trained synthetic models can
  implement or approximate classical linear estimators in context.
- **Our relevance:** coefficient recovery is a cleaner induction measurement
  than repeated arithmetic answers, but remains model/prompt specific.
- **Source:** https://arxiv.org/abs/2211.15661

### Nanda et al. (2023), *Progress Measures for Grokking via Mechanistic Interpretability*

- **Source claim:** small transformers trained on modular addition can form a
  Fourier-like algorithm after a nontrivial learning trajectory.
- **Our relevance:** modular competence is possible in trained networks, but
  weight-training grokking is not inference-time rule induction.
- **Source:** https://arxiv.org/abs/2301.05217

### Wu et al. (2023), *Reasoning or Reciting?*

- **Source claim:** several LLMs lose substantial performance on counterfactual
  variants, including changed arithmetic conventions, despite above-random
  performance.
- **Our relevance:** explicit-rule execution and spontaneous induction must be
  measured separately.
- **Source:** https://arxiv.org/abs/2307.02477

## Label, order, and copying effects

### Zhao et al. (2021), *Calibrate Before Use*

- **Source claim:** few-shot classification can vary sharply with prompt format,
  example choice/order, and answer-label biases, including labels near the end
  of the prompt.
- **Our relevance:** gives external plausibility to a causal order intervention;
  it does not prove anchoring in this dataset.
- **Source:** https://proceedings.mlr.press/v139/zhao21c.html

### Min et al. (2022), *Rethinking the Role of Demonstrations*

- **Source claim:** in several classification/multiple-choice settings,
  randomized demonstration labels hurt surprisingly little while label space,
  input distribution, and format matter.
- **Our relevance:** visible context may shape behavior without rule learning;
  structured numeric induction is a different task, so transfer is limited.
- **Source:** https://aclanthology.org/2022.emnlp-main.759/

### Liu et al. (2024), *Lost in the Middle*

- **Source claim:** location of relevant context changes retrieval/QA
  performance, commonly favoring beginning or end over the middle.
- **Our relevance:** position is a plausible confound even at smaller memory
  sizes; the paper does not imply a monotone last-item effect here.
- **Source:** https://aclanthology.org/2024.tacl-1.9/

### Olsson et al. (2022), *In-context Learning and Induction Heads*

- **Source claim:** induction heads can implement token-pattern copying in small
  transformers; evidence in larger models is more correlational.
- **Our relevance:** provides a plausible copying mechanism, not evidence that
  this closed model uses it for persistent-memory labels.
- **Source:** https://arxiv.org/abs/2209.11895

## Diversity and functional organization

### Li et al. (2021), *Celebrating Diversity in Shared Multi-Agent RL*

- **Source claim:** deliberately induced behavioral diversity can help MARL
  coordination under particular regularized architectures.
- **Our relevance:** behavioral diversity requires a separate utility/alignment
  test; its presence alone is not functional specialization.
- **Source:** https://proceedings.neurips.cc/paper/2021/hash/20aee3a5f4643755a79ee5f6a73050ac-Abstract.html

### Dean et al. (2024), *Emergent Specialization from Participation Dynamics and Multi-Learner Retraining*

- **Source claim:** under a formal participation/retraining model, segmented
  learner equilibria can be stable and socially useful.
- **Our relevance:** this is a useful positive contrast: reinforced allocation
  can produce functional segmentation when competence actually changes. It does
  not describe frozen-weight LLM contextual memory.
- **Source:** https://proceedings.mlr.press/v238/dean24a.html

## Official DeepSeek thinking semantics

- V4 Flash accepts `thinking.type=enabled/disabled` on the same model; thinking
  returns `reasoning_content` separately from final `content`.
- The chat-completion `max_tokens` limits generated completion length. Official
  reasoning-model documentation makes explicit that this includes both chain of
  thought and final output; there is no documented separate final-answer token
  reserve.
- JSON Output still requires an explicit JSON instruction and sufficient output
  budget; `finish_reason=length` indicates truncation.
- `reasoning_effort` offers `high` and `max`; there is no documented lower-effort
  mode that would solve the previous cost/output problem.

Official sources:

- https://api-docs.deepseek.com/api/create-chat-completion
- https://api-docs.deepseek.com/guides/thinking_mode
- https://api-docs.deepseek.com/guides/reasoning_model
- https://api-docs.deepseek.com/guides/json_mode/

## Synthesis for the live hypotheses

The literature supports a three-way discrimination, not a verdict:

1. rank-full function induction is possible in some trained transformers;
2. counterfactual/modular execution may still be fragile;
3. label identity, format, and order can drive outputs independently of useful
   competence.

Therefore the clean tests remain: content-preserving order manipulation for H1,
rank-full coefficient recovery for H4, and explicit-rule held-out execution for
H7. No cited source establishes that persistent memory primarily anchors this
specific model, and none converts the clean-v2 HSE contrast into evidence of
functional specialization.

