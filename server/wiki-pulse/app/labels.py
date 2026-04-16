"""c-TF-IDF cluster-labelling helper.

Computes class-based TF-IDF over article summaries grouped by cluster,
returning the top-N most discriminative terms per cluster.
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer


def ctfidf_labels(
    docs_by_cluster: dict[int, list[str]], top_n: int = 5
) -> dict[int, list[str]]:
    """Return top-N discriminative terms per cluster via class-based TF-IDF.

    Each cluster's summaries are concatenated into a single "class document".
    A CountVectorizer builds the term-frequency matrix (one row per cluster),
    then IDF is computed as ``log(1 + total_articles / (cluster_df + 1))``.
    """
    if not docs_by_cluster:
        return {}

    cluster_ids = sorted(docs_by_cluster.keys())
    class_docs = [" ".join(docs_by_cluster[cid]) for cid in cluster_ids]

    # Skip clusters whose concatenated text is empty
    non_empty = [(i, cid) for i, (cid, doc) in enumerate(zip(cluster_ids, class_docs)) if doc.strip()]
    if not non_empty:
        return {cid: [] for cid in cluster_ids}

    vectorizer = CountVectorizer(
        stop_words="english",
        min_df=1,
        max_features=10_000,
        ngram_range=(1, 2),
    )
    tf = vectorizer.fit_transform(class_docs)  # (n_clusters, n_terms)

    # df = number of clusters containing each term
    df = (tf > 0).sum(axis=0).A1  # dense 1-D array
    total_articles = sum(len(v) for v in docs_by_cluster.values())
    idf = np.log1p(total_articles / (df + 1))

    tfidf = tf.multiply(idf).tocsr()  # element-wise broadcast, ensure CSR for row slicing
    terms = vectorizer.get_feature_names_out()

    result: dict[int, list[str]] = {}
    for i, cid in enumerate(cluster_ids):
        row = tfidf[i].toarray().ravel()
        top_idx = row.argsort()[::-1][:top_n]
        result[cid] = [terms[j] for j in top_idx if row[j] > 0]
    return result
