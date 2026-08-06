# Claude Project更新ガイド

対象：SIMS Merge Claude 1.0.0-RC2

1. Claude Projectの既存Knowledgeファイルをすべて削除します。
2. `Claude-Upload/`を開き、中身をすべてアップロードします。
3. `CLAUDE_PROJECT_INSTRUCTIONS.md`の本文をProject Instructions欄へ貼り付けます。
4. 新しいチャットで`DEPLOYMENT_TEST.md`の確認文を実行します。
5. Product Version `1.0.0-RC2`、Shared Version `3.3.0`が一致することを確認します。

`shared/SNAPSHOT_MANIFEST.json`や`shared/VERSION`は投入禁止です。正本は`shared/platform/SNAPSHOT_MANIFEST.json`です。
