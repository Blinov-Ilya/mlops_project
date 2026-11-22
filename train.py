import csv
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline


ROOT = Path(__file__).resolve().parent


def read_data(split):
    with (ROOT / 'data' / f'{split}.csv').open(encoding='utf-8', newline='') as file:
        rows = list(csv.DictReader(file))
    return [row['text'] for row in rows], [row['category'] for row in rows]


if __name__ == '__main__':
    train_text, train_labels = read_data('train')
    test_text, test_labels = read_data('test')
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
        LogisticRegression(max_iter=500),
    )
    model.fit(train_text, train_labels)
    score = f1_score(test_labels, model.predict(test_text), average='macro')
    print(f'Macro-F1: {score:.4f}')
    joblib.dump(model, ROOT / 'model.joblib')
