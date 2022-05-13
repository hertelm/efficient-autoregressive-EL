import argparse
import json
import pickle
from urllib.parse import unquote
import torch
from tqdm import tqdm

from src.model.efficient_el import EfficientEL


def pickle_load(file_path):
    with open(file_path, "rb") as f:
        obj = pickle.load(f)
    return obj


def json_load(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return data


def url_decode(url):
    return unquote(url).replace("_", " ")


def get_wikipedia_to_qid_mapping():
    wikipedia_to_qid = {}
    WIKI_URL_PREFIX = "https://en.wikipedia.org/wiki/"
    for line in open("data/qid_to_wikipedia_url.tsv"):
        line = line[:-1]
        qid, url = line.split("\t")
        url = url[len(WIKI_URL_PREFIX):]
        url = url_decode(url)
        wikipedia_to_qid[url] = qid
    return wikipedia_to_qid


def read_articles(benchmark_file):
    articles = []
    for line in open(benchmark_file):
        articles.append(json.loads(line))
    return articles


def char_span_to_token_span(tokenizer, tokens, char_span):
    start = end = None
    for i in range(0, len(tokens)):
        decoded = tokenizer.convert_tokens_to_string(tokens[:(i + 1)])
        pos = len(decoded)
        if decoded.endswith("�"):
            pos -= 1
        if start is None and char_span[0] < pos:
            start = i
        if end is None and char_span[1] <= pos:
            end = i
            break
    if start > 0:
        start += 1
    end += 1
    return start, end


class CandidateGenerator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.entities = set(json_load("data/entities.json"))
        print(len(self.entities), "entities")
        self.mentions = set(json_load("data/mentions.json"))
        print(len(self.mentions), "mentions")
        self.mention_to_candidates_dict = pickle_load("data/mention_to_candidates_dict.pkl")
        print(len(self.mention_to_candidates_dict), "mentions with candidates")

    def add_anchors_and_candidates(self, article: dict):
        anchors = []
        candidates = []
        tokens = self.tokenizer.tokenize(article["text"])
        for label in article["labels"]:
            span = label["span"]
            mention = article["text"][span[0]:span[1]]
            if mention not in self.mentions:
                continue
            mention_candidates = [c for c in self.mention_to_candidates_dict.get(mention, []) if c in self.entities]
            if len(mention_candidates) == 0:
                continue
            token_span = char_span_to_token_span(self.tokenizer, tokens, span)
            anchor = (token_span[0], token_span[1], "")
            anchors.append(anchor)
            candidates.append(mention_candidates)
        article["anchors"] = anchors
        article["candidates"] = candidates


class WikipediaToWikidataMapper:
    def __init__(self):
        self.wikipedia_to_qid = get_wikipedia_to_qid_mapping()
        print(len(self.wikipedia_to_qid), "Wikipedia to QID mappings")
        self.redirects = pickle_load("data/link_redirects.pkl")
        print(len(self.redirects), "Wikipedia redirects")

    def wiki2qid(self, wikipedia_title):
        if wikipedia_title in self.redirects:
            wikipedia_title = self.redirects[wikipedia_title]
        if wikipedia_title in self.wikipedia_to_qid:
            return self.wikipedia_to_qid[wikipedia_title]
        return wikipedia_title


def predict(article, model, wiki2qid_mapper):
    text = article["input"] if "input" in article else article["text"]
    anchors = article["anchors"]
    candidates = article["candidates"]

    result = model.sample([text], anchors=[anchors], candidates=[candidates], all_targets=True)

    predictions = []
    if len(result) > 0:
        for span in result[0]:
            entity = wiki2qid_mapper.wiki2qid(span[2][0][0])
            candidates = [wiki2qid_mapper.wiki2qid(candidate[0]) for candidate in span[2] if len(candidate[0]) > 0]
            prediction = {
                "span": [span[0], span[1]],
                "recognized_by": "efficient-EL",
                "linked_by": "efficient-EL",
                "candidates": candidates,
                "id": entity
            }
            predictions.append(prediction)

    return predictions


def main(args):
    print("load model...")
    model = EfficientEL.load_from_checkpoint("data/model.ckpt").eval()

    if torch.cuda.is_available():
        print("move model to GPU...")
        model = model.to("cuda")

    print("prepare candidate generator...")
    candidate_generator = CandidateGenerator(model.tokenizer)

    print("prepare Wikipedia to Wikidata mapper...")
    wiki2qid_mapper = WikipediaToWikidataMapper()

    articles = read_articles(args.input_file)

    with open(args.output_file, "w") as out_file:
        for article in tqdm(articles):
            if not "candidates" in article:
                candidate_generator.add_anchors_and_candidates(article)
            predictions = predict(article, model, wiki2qid_mapper)
            article["entity_mentions"] = predictions
            out_file.write(json.dumps(article) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)
    parser.add_argument("output_file", type=str)
    args = parser.parse_args()
    main(args)
