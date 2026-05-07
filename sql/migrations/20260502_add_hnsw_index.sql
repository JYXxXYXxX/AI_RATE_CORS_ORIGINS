-- 为 document_sections.embedding 创建 HNSW 索引，加速跨文档相似度查询
-- 注意：HNSW 索引在写入时有一定开销，适合读多写少的场景
-- 如果写入压力极大，可考虑 IVF 索引替代

CREATE INDEX IF NOT EXISTS idx_sections_embedding_hnsw
ON document_sections
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
