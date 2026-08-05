# Product Specification

SIMS Mergeは、複数記事を単純結合するツールではなく、検索意図・クエリ・本文・評価・収益要素を比較し、安全な統合または役割分担を設計します。

## 出力判断

- `MERGE_REQUIRED`
- `ROLE_SEPARATION_REQUIRED`
- `KEEP_BOTH`
- `REDIRECT_CANDIDATE`
- `NOINDEX_CANDIDATE`
- `DELETE_CANDIDATE`
- `EVIDENCE_INSUFFICIENT`

高リスク処置は必ず`USER_DECISION_REQUIRED`として扱います。
