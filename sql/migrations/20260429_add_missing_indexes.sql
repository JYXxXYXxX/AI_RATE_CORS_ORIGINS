-- 为核心表添加缺失的索引以提升查询性能

-- user_sessions: 按 user_id 查询用户会话
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
    ON public.user_sessions USING btree (user_id);

-- analysis_runs: 按 document_id 查询文档的分析记录
CREATE INDEX IF NOT EXISTS idx_analysis_runs_document_id
    ON public.analysis_runs USING btree (document_id, created_at DESC);

-- report_snapshots: 按 run_id 查询报告快照
CREATE INDEX IF NOT EXISTS idx_report_snapshots_run_id
    ON public.report_snapshots USING btree (run_id);

-- proxy_predictions: 按 run_id 查询代理预测结果
CREATE INDEX IF NOT EXISTS idx_proxy_predictions_run_id
    ON public.proxy_predictions USING btree (run_id);

-- document_sections: 按 document_id 查询段落（高频）
CREATE INDEX IF NOT EXISTS idx_document_sections_document_id
    ON public.document_sections USING btree (document_id, section_index);

-- section_scores: 按 run_id 查询分数
CREATE INDEX IF NOT EXISTS idx_section_scores_run_id
    ON public.section_scores USING btree (run_id);

-- section_scores: 唯一约束防止重复评分
CREATE UNIQUE INDEX IF NOT EXISTS idx_section_scores_unique
    ON public.section_scores (run_id, document_section_id, score_type);

-- cnki_feedback: 按 document_id 查询反馈记录
CREATE INDEX IF NOT EXISTS idx_cnki_feedback_document_id
    ON public.cnki_feedback USING btree (document_id, created_at DESC);

-- documents: 按 doc_hash 查找（已有 UNIQUE 约束，此处确认）
-- documents: 按 status 筛选
CREATE INDEX IF NOT EXISTS idx_documents_status
    ON public.documents USING btree (status);

-- similarity_matches: 按 run_id 查询相似匹配
CREATE INDEX IF NOT EXISTS idx_similarity_matches_run_id
    ON public.similarity_matches USING btree (run_id);

-- model_registry: 按 model_type + is_active 查询活跃模型
CREATE INDEX IF NOT EXISTS idx_model_registry_active
    ON public.model_registry USING btree (model_type, is_active)
    WHERE is_active = true;
