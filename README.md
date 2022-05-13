# efficient-autoregressive-EL on arbitrary benchmarks

## 0. Introduction

[efficient-autoregressive-EL](https://github.com/nicola-decao/efficient-autoregressive-EL)
requires pre-computed mention spans and candidate sets.
The original repository contains a pre-processed version of the AIDA-CoNLL benchmark,
but no other benchmark.

This repository provides a method to generate mention spans and candidate sets
for benchmarks in the Article JSONL format (introduced by Elevant),
and a Docker setup to run efficient-autoregressive-EL on them.

## 1. Installation

### Option 1: Install with Docker

```
docker build -t efficient-el .
```

### Option 2: Install with virtualenv

```
python3.8 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Needed data

Download the pre-processed data from
[efficient-autoregressive-EL](https://github.com/nicola-decao/efficient-autoregressive-EL)
and get the files *link_redirects.pkl*, *mention_to_candidates_dict.pkl*, *qid_to_wikipedia_url.tsv*
that can be generated with [reproducible GENRE](https://github.com/hertelm/GENRE),
and put everything in a folder 'data'.

Alternatively, if you are on a machine from the Algorithms & Datastructures chair,
you can mount the directory '/nfs/students/matthias-hertel/efficent-el-reproducibility-data' to the folder 'data'.

## 3. Start container

```
docker run -it -v $PWD/data:/workspace/data efficient-el bash
```

or

```
docker run -it -v /nfs/students/matthias-hertel/efficent-el-reproducibility-data:/workspace/data efficient-el bash
```

## 4. Run model

Run the model on a file in Article JSONL format
(described in [Elevant](https://github.com/ad-freiburg/elevant)).

Candidate sets will be added for all ground truth mentions.
For all other mentions (false positive detections by the model),
the model will predict 'NIL' as the entity.

```
python3 main.py <INPUT_FILE> <OUTPUT_FILE>
```

Example call:

```
python3 main.py example_article.jsonl output.jsonl
```