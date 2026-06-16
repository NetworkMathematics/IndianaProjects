A place to organize our research.

We have preprints:
* [Math Natural Language Inference: This Should Be Easy!](https://aclanthology.org/2025.starsem-1.14.pdf) presented  at 14th Joint Conference on Lexical and Computational Semantics (*SEM 2025), Nov 2025.
* [KnowTeX: Visualizing Mathematical Dependencies](https://arxiv.org/pdf/2601.15294) submitted.
* [Extracting Mathematical Concepts with Large Language Models](https://arxiv.org/pdf/2309.00642) presented at 14th MathUI Workshop 2023, CICM2023.

Our data:
* [TAC](http://www.tac.mta.ca/tac/) [abstracts corpus](https://github.com/ToposInstitute/tac-corpus) (1995-2020) at Topos Institute
  * [goldilock sentences](https://github.com/vcvpaiva/NLIMath/blob/main/436sentences.txt) (433 sentences)
  * [all sentences](https://github.com/vcvpaiva/NLIMath/blob/main/3k_tac.txt) (actually 2930 sentences)
* [nLab](https://github.com/ToposInstitute/nlab-corpus) corpus (up to 2020) ~175K sentences
* [Chicago Notes](https://github.com/vcvpaiva/Lucy/blob/main/BasicGlossary/chicagonotes.txt) a version of Chicago notes as a single .txt file with 1335 sentences
* MathNLI corpora:
  * [Seed corpus](https://github.com/vcvpaiva/NLIMath/blob/main/NLIcorpora/SeedNLI%20corpus%20-%20Sheet1.csv)
  * [GPT4-generated NLI pairs](https://github.com/vcvpaiva/NLIMath/blob/main/NLIcorpora/GPT4-NLI%20corpus%20-%20Sheet1.csv)

Our prototype for annotation: 

[MathAnnotator](https://gaoq111.github.io/math_concept_annotation/)


## Toward a Machine-Readable Database of Categorical Terms

(Lessons from Large Language Models and Human-Curated Resources)

We're completing a database of terms of Category Theory, extracted from the TAC/Chicago notes corpora above.

Our data is in the spreadsheets https://docs.google.com/spreadsheets/d/1jLzuvuaLIcRTIQPwQ65fL3o9gzasplJ52eEUFJhhMSk/edit?gid=105714284#gid=105714284 and

 https://docs.google.com/spreadsheets/d/1yy3NjhP0mj75ws0k3qnCbFCI-giSHCqVwUW_8CGblEQ/edit?usp=sharing

 A static version is in the directory [TermsDB](https://github.com/NetworkMathematics/TermsDB/blob/main/README.md).

 ### Issues
 
 We end up with too many concepts extracted by the LLMs, which we could not find in the human-curated resources.
 
 There were two reasons for that:
 
 1. We were extracting concepts from papers in research mathematics, so the human-curated resources were bound to lag behind:
    (too many new concepts won't make it to the canon of mathematics).

    LLMs could only extract terms that `looked-like' mathematics, things like ``associative magma" were considered concepts.
    
 2. If we changed the corpus to have a golden notion of concept and its definition, it should be easier to establish a kernel of guaranteed concepts, right?
    
 3. We changed the corpus to Lucy Horowitz's "Chicago Notes". This is a shorter corpus, only 1335 sentences which have mathematical concepts attached to it -- it's a basic glossary. It should work as a basic, golden standard seed for our glossary.
 
 However, this does not work directly either, because different mathematicians write concepts in different ways. 
 
 For example, [MathGloss](https://mathgloss.github.io/MathGloss/web/) has 
 
 *Baire function* (functions obtained from continuous functions by transfinite iteration of the operation of forming pointwise limits of sequences of functions) in Wikidata. 
 
 But Chicago Notes has:
 
 Definition: The *Baire classes of continuous real-valued functions* on a topological space are defined as follows:

   * continuous functions are Baire-0;
   * functions that are the pointwise limit of a sequence of continuous functions are Baire-1;
   * for all alpha in N, functions that are the pointwise limit of a sequence of functions of Baire class less than  alpha are Baire-alpha.

These two definitions seem equivalent to me, but I don't actually know if they are. Math needs to be precise, but we want a human-like definition, not a totally formal one, as this commits us to a particular formalization.
 
