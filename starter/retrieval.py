"""Dense, TF-IDF and reciprocal rank fusion on one Day 6 chunk snapshot."""
import hashlib
import json
import time

from baseline import TfidfIndex, pack_context

METHODS = ('dense', 'lexical', 'hybrid')


class QuestionContextSelector:
    """Rerank the cumulative candidate pool by the ORIGINAL question's E5 vector."""
    def __init__(self, dense, question, lock=None):
        from contextlib import nullcontext
        self.lock = lock or nullcontext()
        self.dense = dense
        self.question = question
        self.vector = None
        self.calls = []

    def __call__(self, candidates, *, budget):
        start = time.perf_counter()
        unique = {c['id']: c for c in candidates}
        with self.lock:
            if self.vector is None:
                self.vector = self.dense.embedder.embed_query(self.question)
            vector = self.dense.store._vector(self.vector)
            ranked = self.dense.store.connection.execute('''SELECT chunk_id,
                1-(embedding <=> %s::vector) AS context_score
                FROM day6_ingestion.chunks WHERE strategy=%s AND chunk_id=ANY(%s)
                ORDER BY embedding <=> %s::vector, chunk_id''',
                (vector, self.dense.strategy, list(unique), vector)).fetchall()
        if len(ranked) != len(unique):
            raise ValueError('Context candidate missing from database snapshot')
        context, ids = pack_context([unique[r['chunk_id']] for r in ranked], budget=budget)
        self.calls.append({'question': self.question, 'ranking': ranked, 'context_ids': ids,
                           'budget_chars': budget, 'elapsed_seconds': time.perf_counter()-start})
        return context, ids


def reciprocal_rank_fusion(rankings, *, top_k, constant=60):
    if top_k < 1 or constant < 1:
        raise ValueError('top_k and RRF constant must be positive')
    merged = {}
    for name, rows in rankings.items():
        seen = set()
        for rank, row in enumerate(rows, 1):
            cid = row['id']
            if cid in seen:
                raise ValueError('Duplicate chunk in a component ranking')
            seen.add(cid)
            if cid not in merged:
                merged[cid] = {**row, 'score': 0.0, 'component_ranks': {}, 'component_scores': {}}
            item = merged[cid]
            item['score'] += 1 / (constant + rank)
            item['component_ranks'][name] = rank
            item['component_scores'][name] = row['score']
    return sorted(merged.values(), key=lambda row: (-row['score'], row['id']))[:top_k]


class RetrievalSuite:
    def __init__(self, dense, method='dense', candidates=10, rrf_constant=60):
        if method not in METHODS or candidates < 1 or rrf_constant < 1:
            raise ValueError('Invalid retrieval configuration')
        self.dense = dense
        self.method, self.candidates, self.rrf_constant = method, candidates, rrf_constant
        self.calls = []
        rows = dense.store.connection.execute('''SELECT chunk_id AS id, document_id AS source_id,
            source, page, text, metadata FROM day6_ingestion.chunks
            WHERE strategy=%s ORDER BY chunk_id''', (dense.strategy,)).fetchall()
        if len(rows) != dense.info['chunks']:
            raise ValueError('Chunk snapshot changed during initialization')
        self.lexical = TfidfIndex(rows)
        self.info = {**dense.info, 'method': method, 'hybrid_candidates_per_retriever': candidates,
                     'rrf_constant': rrf_constant,
                     'chunk_snapshot_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True,
                         ensure_ascii=False).encode()).hexdigest(),
                     'lexical': 'NFC/casefold word tokens; TF-IDF L2 cosine; global corpus IDF'}

    def search(self, query, *, filters, top_k):
        if not isinstance(query, str) or not query.strip() or type(top_k) is not int or top_k < 1:
            raise ValueError('Invalid query/top_k')
        filters = filters or {}
        for name, value in filters.items():
            if name not in ('chapter', 'language'):
                raise ValueError('Unsupported filter')
            if name == 'chapter' and type(value) is not int:
                raise ValueError('chapter must be integer')
            if name == 'language' and not isinstance(value, str):
                raise ValueError('language must be string')
        start = time.perf_counter()
        call = {'method': self.method, 'query': query, 'filters': filters, 'top_k': top_k}
        self.calls.append(call)
        try:
            cutoff = max(top_k, self.candidates) if self.method == 'hybrid' else top_k
            components = {}
            if self.method in ('dense', 'hybrid'):
                components['dense'] = self.dense.search(query, filters=filters, top_k=cutoff)
            if self.method in ('lexical', 'hybrid'):
                # Rank all positive lexical matches before applying the common filter
                # and cutoff, so filtered-out rows never consume candidate slots.
                rows = self.lexical.search(query, top_k=len(self.lexical.chunks))
                components['lexical'] = [r for r in rows if all(
                    r['metadata'].get(k) == v for k, v in filters.items())][:cutoff]
            results = (reciprocal_rank_fusion(components, top_k=top_k, constant=self.rrf_constant)
                       if self.method == 'hybrid' else components[self.method])
            results = [{**row, 'retrieval_method': self.method, 'rank': rank}
                       for rank, row in enumerate(results, 1)]
            call.update(components=components, results=results)
            return results
        except Exception as exc:
            call['error_type'] = type(exc).__name__
            raise
        finally:
            call['elapsed_seconds'] = time.perf_counter() - start

    def close(self):
        self.dense.close()
