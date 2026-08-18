# Contextual Compositionality Analysis

Briefly: I anticipated that a term that can be expressed as a simple combination of its component words is a less useful term. So I made a measure of compositionality, and compared it to a couple of other metrics of quality we have. There was generally a correlation, as expected, though with some nuance of context.

## Data

We have three datasets:

1. **v4_combined**: a binary dataset, where for each term, each of the 3 LLMs was given a 1 if it considered the term a mathematical concept, and 0 otherwise. Similarly, each of 4 human corpora (nlab, planetmath, wikidata, tac-corpus) was given a 1 if the term was found in the corpus, and 0 otherwise. The v4_combined dataset was tested on all terms for which at least one LLM had a 1.
2. **0624-chicago_mappings_agreed_grounded_llm**: this dataset only includes terms which all 3 LLMs identified as a mathematical concept, but also includes which sentence each LLM identified, taken from the Chicago corpus. Additionally, an LLM (which?) evaluated the top 20 matching Wikidata pages: if any seemed to be the concept at hand, the term was marked `grounded,` and `rejected` otherwise.
3. **Merged**: this dataset includes only terms which are found in both datasets, and contains the Chicago corpus context, the grounding, and the 4 human corpora.

## Embedding

Each mathematical term is embedded using `BAAI/bge-small-en-v1.5`. Three embedding conditions are evaluated independently:

1. **No context**: the term itself.
2. **Basic context**: `In mathematics, <term>`.
3. **Corpus context**: the term extracted from each associated Chicago-corpus sentence, using a window of five words on either side of the term. If an exact match for the term cannot be found in a sentence, that context is skipped.

## Compositionality

The motivation for this approach is to see whether a term can be expressed as a combination of its components, or whether it is expressing an idea that is not clearly anticipated from its components. In the former case, we anticipate less helpful concepts composed by appending terms together, so we expect a high degree of compositionality to correlate with lower quality.

For each context, compositionality is computed using binary partitions of multi-word terms. Any single split is permitted provided both components contain at least one word of at least two letters.

For a term split into components $A$ and $B$, the component embeddings are computed in the same context as the original term. The full-term embedding is projected onto the linear basis spanned by the two component embeddings. The score is based on the cosine similarity between the full-term embedding and its projection:

$$
C = \cos(E_{term}, \operatorname{proj}_{A,B}(E_{term})).
$$

Higher scores indicate greater compositionality: the term embedding is more closely recoverable from its component embeddings. For a term with multiple valid splits, the highest-scoring split is retained. This naturally increases compositionality for longer terms, a confound which is controlled for later.

For corpus contexts, the 3 models may or may not find different sentences. Duplicate sentences are discarded, then compositionality is computed separately for every distinct context. Context embeddings never interact with one another; the resulting scores are averaged only after the individual contexts have been evaluated.

## Analysis and Results

### Human occurrence count

Compositionality was compared across terms with 0 to 4 occurrences in human corpora from the v4_combined dataset. This was performed for all terms, as well as separately for terms of 2, 3, or 4+ words. This was done for both the no-context case, and the basic context case.

Low compositionality was positively correlated with greater frequency in human corpora for both contexts. The effect size was strongest when all terms were included, since longer terms are both more compositional, and less likely to occur in human corpora. However, the results remained statistically significant for bigrams. 3-grams, and especially 4-grams, became increasingly skewed away from human corpora.

### Grounded and rejected

Compositionality was compared across terms marked as `grounded` or `rejected` in the Chicago dataset. This was performed for all 3 contexts.

Low compositionality was positively correlated with grounding, except in the basic context case. In the basic context case, components which have common use outside of mathematics were more significantly benefitted (as this context only clarifies that it should be taken in a mathematical context), but components which have common use are also those for which their mathematical use were more likely to be after the first 20 Wikidata entries, and thus were more likely to be false negatives. Thus, the basic context case disproportionately altered compositionality for both true positives and false negatives, eliminating the effect.

Additionally, human corpora occurrence counts were compared between `grounded` and `rejected` terms. There was an unsurprising correlation between grounded terms and human corpora occurrence.

### Cross-context

Compositionality was compared across the three context conditions using the Chicago dataset, to determine which terms are affected by which contexts:

- no context vs. basic context
- no context vs. corpus context
- basic context vs. corpus context

Items like `natural number,` `lie group`, and `partial order` were highly benefitted by basic context, which aligns with the explanation given above: words like `normal` and `group` are common outside of mathematical contexts, so adding even simple context greatly alters the compositionality. On the other hand, items like `homotopy equivalent` saw minimal change, as both component words are strongly associated with mathematics already.