# Contextual Compositionality Analysis
Soren DeHaan, 17th August 2026, 8th September 2026

Briefly: A mathematical term which can be expressed as a simple combination of its component words seems to be a less useful term. I made a measure of compositionality which measures how much a term can be approximated by its components, and compared it to a couple of other metrics of quality we have. There was generally a correlation, as expected, though with some nuance of context.

## Compositionality

The goal of this approach is to evaluate ``how much'' of the meaning of a multi-word expression is apparent from its components, and how much necessitates an understanding of the expression as a whole. If a multi-word expression is more compositional, then it is likely to be less useful to define independently of its components, whereas an expression which necessitates individual explanation is closer to the kind of concept we would want to identify.

For a lay example, consider the phrases "green dog" and "hot dog". The former is compositional (a dog which is green) and the latter is non-compositional (a "dog which is hot" is not what is meant by "hot dog"). Our goal is to identify to what degree the meaning of the expression is derived from the components, versus the interaction of the components.

To do this, we use the embeddings of a language model as a proxy for (distributional) meaning, so that our question becomes "does the composite phrase occur in different texts as compared to either of its components?" We might imagine that a purely compositional item is some nearly-linear combination of its components, though the proportion of one component to another may vary. Thus, we take the embeddings of each of an expression's components and construct a linear basis spanned by the component embeddings. We then evaluate how far the expression's embedding is from the projection of its embedding onto the span (using cosine similarity as the standard).

A few details are important to state. First, we are generally concerned with the possibility that any singular addition to the term is redundant. For instance, consider the phrase "large hot dog". Even if "hot dog" is not compositional, the addition of "large" is, and therefore the expression as a whole would not be worth identifying. For this reason, we care about whether there is *any* way to split the expression that makes it compositional. For longer multi-word expressions, we will take the maximum of all compositionality scores among all ways to split the expression without changing word order (and such that there is at least one word of length at least two on both sides).

More formally, over the set of all sub-expression pairs $A,B$ such that $AB = term$ by concatenation:

$$
C = \max_{A,B}(\cos(E_{term}, \mathop{\text{proj}}_{A,B}(E_{term}))).
$$

Higher scores indicate greater compositionality: the term embedding is more closely recoverable from its component embeddings.

<> For datasets that include multiple corpus contexts, different models may or may not find different sentences. Duplicate sentences are discarded, then compositionality is computed separately for every distinct context. Context embeddings never interact with one another; the resulting scores are averaged only after the individual contexts have been evaluated.

## Data

For proof of concept, I initially used several old datasets. However, the version in this database (that is- "data/mathgloss_chicago_611terms_with_compositionality.csv") is evaluated directly on the terms identified in "data/mathgloss_chicago_ground_truth_611terms.txt".

## Embedding

Each mathematical term is embedded using `BAAI/bge-small-en-v1.5`. Other embedding models could be used (especially one fine-tuned for mathematics), but I anticipate the basic context is sufficient for most. Three embedding conditions can be evaluated independently:

1. **No context**: the term itself.
2. **Basic context**: `In mathematics, <term>`.
3. **Corpus context**: the term extracted from each associated Chicago-corpus sentence, using a window of five words on either side of the term. If an exact match for the term cannot be found in a sentence, that context is skipped. This is only used for datasets that include their associated corpus sentences, so is not in the current dataset.

## Analysis and Results

To interpret the current results, I recommend looking at the basic_context_percentile column in "data/mathgloss_chicago_611terms_with_compositionality.csv". The higher this value, the more compositional it is, relative to other terms in the corpus. In general, a lower value indicates a term which is not easily expressed as a combination of its components, and a higher value means the term is more directly derived from its components. Thus, I expect _lower values_ to correspond with _preferred terms_.

To quantitatively evaluate this, we'll need to compare the scores against another metric, and see if there's useful correlation. In the past, I measured against a dataset which included human corpus occurrence rate, and saw expected correlation, but the current dataset does not have that metric. As a result, analysis is ongoing.
