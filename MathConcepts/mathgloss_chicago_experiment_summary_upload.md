# MathGloss Chicago Concept Extraction Summary

## Setting

We want to test how good the LLM pipeline + wikidata grounding is. Previously we had a mismatch between the corpus we used to extract the concepts (the 450 lines "chicago_mappings.csv") and the "ground truth" human annotated set of concpets (only 395 terms; the source sentences of this set of concepts is unknown).

We noticed that there are 611 markdown files under the "Chicago" folder and each file is defining a concept with concepts in the definition sentences marked with hyperlinks to Mathgloss. So from there we can get a seemingly "ground truth" set of concepts that can be extracted from these 611 sentences (i.e., the terms that are defined + the terms with hyperlink in the definition sentences). And this is the source corpus that we are using this time:

- Source markdown folder: [MathGloss/chicago/](https://github.com/MathGloss/MathGloss/tree/main/chicago)
- Extracted sentence corpus formed from the above markdown files: [data/mathgloss_chicago_definition_sentences.txt](https://drive.google.com/file/d/1pyEG4Q_fLb3IzxKx0CaolNfKVKA0gOtP/view?usp=drive_link)
- Sentence metadata CSV: [data/mathgloss_chicago_definition_sentences.csv](https://docs.google.com/spreadsheets/d/1cKQ4N0DxcgQ9tlbmdHPfBs1qwjPCvYIvjmUKr6fgU-I/edit?gid=108875846#gid=108875846)

The corpus contains 611 markdown pages. Each input sentence is the page title followed by its definition text, e.g. `Abelian Group: ...`.

## Machine Extraction

We ran the 3-LLM extraction pipeline with UD parsing given as part of the context to help them break out the sentences:

- Combined concept CSV: [outputs/mathgloss_chicago_definitions_udep/mathgloss_chicago_definitions_udep_combined_concepts.csv](https://docs.google.com/spreadsheets/d/1cKQ4N0DxcgQ9tlbmdHPfBs1qwjPCvYIvjmUKr6fgU-I/edit?gid=598315717#gid=598315717)

The all-model-agreed machine set has 911 terms.

## Grounding Step

We grounded only the terms agreed on by all three LLMs.

- Grounded agreed-term CSV: [outputs/mathgloss_chicago_definitions_udep_grounded_llm/mathgloss_chicago_definitions_udep_agreed_grounded_llm.csv](https://docs.google.com/spreadsheets/d/1rdqz7vqddWr-msEab0rewEzeSSTJ6db4aKSM60C5f4E/edit?gid=967311553#gid=967311553)

After retrying transient Wikidata/Wikipedia failures, the grounded set has 622 terms. There are no remaining `search failed` or HTTP 429 rows.

## Ground Truth Set

The ground truth set is built from the human-authored MathGloss markdown files:

1. Every page title is included.
2. Every markdown hyperlink bracket text in the definition body is included.
3. Front matter, permalink metadata, image links, and `Wikidata ID` links are excluded.
4. The bracket text is used as the term, not the URL target. For example, `[adjoint map](.../adjoint_map_of_a_Lie_group)` contributes `adjoint map`.

Files:

- Ground truth metadata CSV: [data/mathgloss_chicago_ground_truth_terms.csv](https://docs.google.com/spreadsheets/d/1cKQ4N0DxcgQ9tlbmdHPfBs1qwjPCvYIvjmUKr6fgU-I/edit?gid=1277366660#gid=1277366660)

The current ground truth set has 962 terms.

## Comparison Files

- Machine-agreed terms with source markdown files, definition sentences, grounded flags, and ground-truth match flags: [data/mathgloss_chicago_machine_agreed_review.csv](https://docs.google.com/spreadsheets/d/1cKQ4N0DxcgQ9tlbmdHPfBs1qwjPCvYIvjmUKr6fgU-I/edit?gid=1685887564#gid=1685887564)
- Ground-truth terms with machine-agreed coverage flags: [data/mathgloss_chicago_ground_truth_coverage_review.csv](https://docs.google.com/spreadsheets/d/1cKQ4N0DxcgQ9tlbmdHPfBs1qwjPCvYIvjmUKr6fgU-I/edit?gid=644477911#gid=644477911)

![Term-set Venn diagram](data/mathgloss_chicago_termset_venn.png)

Current summary:

- Ground truth: 962 terms
- Machine agreed: 911 terms
- Machine grounded: 622 terms
- Agreed overlap with ground truth: 562
- Ground truth missing from agreed: 400
- Agreed outside ground truth: 349
- Grounded overlap with ground truth: 408
- Ground truth missing from grounded: 554
- Grounded outside ground truth: 214

