-- 扩展 cnki_feedback 表，增加 details JSONB 字段存储知网报告解析详情

ALTER TABLE public.cnki_feedback
    ADD COLUMN IF NOT EXISTS details jsonb DEFAULT '{}'::jsonb NOT NULL;

-- 为 details 字段添加 GIN 索引以支持 JSON 查询
CREATE INDEX IF NOT EXISTS idx_cnki_feedback_details_gin
    ON public.cnki_feedback USING gin (details);
