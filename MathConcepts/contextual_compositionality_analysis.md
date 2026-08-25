# Contextual Compositionality Analysis
Soren DeHaan, 17th August 2026

Briefly: I anticipated that a mathematical term that can be expressed as a simple combination of its component words is a less useful term. So I made a measure of compositionality, and compared it to a couple of other metrics of quality we have. There was generally a correlation, as expected, though with some nuance of context.

## Data

For proof of concept, I used several old datasets. The version in this database (that is- "data/mathgloss_chicago_611terms_with_compositionality.csv") is evaluated directly on the terms identified in "data/mathgloss_chicago_ground_truth_611terms.txt".

## Embedding

Each mathematical term is embedded using `BAAI/bge-small-en-v1.5`. Other embedding models could be used (especially one fine-tuned for mathematics), but I anticipate the basic context is sufficient for most. Three embedding conditions can be evaluated independently:

1. **No context**: the term itself.
2. **Basic context**: `In mathematics, <term>`.
3. **Corpus context**: the term extracted from each associated Chicago-corpus sentence, using a window of five words on either side of the term. If an exact match for the term cannot be found in a sentence, that context is skipped. This is only used for datasets that include their associated corpus sentences, so is not in the current dataset.

## Compositionality

The motivation for this approach is to see whether a term can be expressed as a combination of its components, or whether it is expressing an idea that is not clearly anticipated from its components. In the former case, we anticipate less helpful concepts composed by appending terms together, so we expect a high degree of compositionality to correlate with lower quality.

For each context, compositionality is computed using binary partitions of multi-word terms. Any single split is permitted provided both components contain at least one word of at least two letters.

For a term split into components $A$ and $B$, the component embeddings are computed in the same context as the original term. The full-term embedding is projected onto the linear basis spanned by the two component embeddings. The score is based on the cosine similarity between the full-term embedding and its projection:

$$
C = \cos(E_{term}, \mathop{\text{proj}}_{A,B}(E_{term})).
$$

Higher scores indicate greater compositionality: the term embedding is more closely recoverable from its component embeddings. For a term with multiple valid splits, the highest-scoring split is retained. This naturally increases compositionality for longer terms, a confound which can be separated out and controlled for later.

For datasets that include multiple corpus contexts, different models may or may not find different sentences. Duplicate sentences are discarded, then compositionality is computed separately for every distinct context. Context embeddings never interact with one another; the resulting scores are averaged only after the individual contexts have been evaluated.

## Analysis and Results

To interpret the current results, I recommend looking at the basic_context_percentile column in "data/mathgloss_chicago_611terms_with_compositionality.csv". The higher this value, the more compositional it is, relative to other terms in the corpus. In general, a lower value indicates a term which is not easily expressed as a combination of its components, and a higher value means the term is more directly derived from its components. Thus, I expect _lower values_ to correspond with _preferred terms_.

To quantitatively evaluate this, we'll need to compare the scores against another metric, and see if there's useful correlation. In the past, I measured against a dataset which included human corpus occurrence rate, and saw expected correlation, but the current dataset does not have that metric. As a result, analysis is ongoing.
