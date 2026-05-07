-- 核心数据库 schema: 文档、分析、检测、代理预测等基础表
-- 运行顺序: 先于 20260428_c_end_foundation.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 文档表
CREATE TABLE IF NOT EXISTS public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying(500),
    filename character varying(500) NOT NULL,
    subject character varying(100),
    degree_level character varying(50),
    language character varying(20) DEFAULT 'zh-CN' NOT NULL,
    doc_hash character varying(64) NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    section_count integer DEFAULT 0 NOT NULL,
    status character varying(30) DEFAULT 'uploaded' NOT NULL,
    source_type character varying(30) DEFAULT 'upload' NOT NULL,
    original_file_path text,
    cleaned_text_path text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_doc_hash_key UNIQUE (doc_hash);

-- 文档段落表
CREATE TABLE IF NOT EXISTS public.document_sections (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    section_index integer NOT NULL,
    paragraph_index integer,
    section_type character varying(50) DEFAULT 'body' NOT NULL,
    section_title character varying(500),
    text_preview text,
    content text NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    embedding vector(768),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.document_sections
    ADD CONSTRAINT document_sections_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.document_sections
    ADD CONSTRAINT document_sections_document_id_fkey
    FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

-- 分析运行表
CREATE TABLE IF NOT EXISTS public.analysis_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_type character varying(50) DEFAULT 'full_analysis' NOT NULL,
    provider character varying(50) DEFAULT 'local' NOT NULL,
    provider_version character varying(120),
    status character varying(30) DEFAULT 'queued' NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone
);

ALTER TABLE ONLY public.analysis_runs
    ADD CONSTRAINT analysis_runs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.analysis_runs
    ADD CONSTRAINT analysis_runs_document_id_fkey
    FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

-- 段落分数表
CREATE TABLE IF NOT EXISTS public.section_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    document_section_id uuid NOT NULL,
    score_type character varying(30) NOT NULL,
    raw_score double precision DEFAULT 0 NOT NULL,
    normalized_score double precision DEFAULT 0 NOT NULL,
    risk_level character varying(20) DEFAULT 'low' NOT NULL,
    reasons jsonb DEFAULT '[]'::jsonb NOT NULL,
    signals jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_run_id_fkey
    FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_section_id_fkey
    FOREIGN KEY (document_section_id) REFERENCES public.document_sections(id) ON DELETE CASCADE;

-- 相似匹配表
CREATE TABLE IF NOT EXISTS public.similarity_matches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    document_section_id uuid NOT NULL,
    matched_source character varying(500),
    matched_title character varying(500),
    matched_snippet text,
    similarity_score double precision DEFAULT 0 NOT NULL,
    overlap_chars integer DEFAULT 0 NOT NULL,
    match_type character varying(50) DEFAULT 'semantic' NOT NULL,
    source_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.similarity_matches
    ADD CONSTRAINT similarity_matches_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.similarity_matches
    ADD CONSTRAINT similarity_matches_run_id_fkey
    FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;

-- 提供商数据载荷表
CREATE TABLE IF NOT EXISTS public.provider_payloads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    provider character varying(50) NOT NULL,
    payload_type character varying(30) NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.provider_payloads
    ADD CONSTRAINT provider_payloads_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.provider_payloads
    ADD CONSTRAINT provider_payloads_run_id_fkey
    FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;

-- 代理预测表
CREATE TABLE IF NOT EXISTS public.proxy_predictions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_id uuid NOT NULL,
    model_version character varying(200),
    scene_key character varying(100),
    predicted_cnki_dup double precision,
    predicted_cnki_dup_low double precision,
    predicted_cnki_dup_high double precision,
    predicted_cnki_aigc double precision,
    predicted_cnki_aigc_low double precision,
    predicted_cnki_aigc_high double precision,
    confidence double precision,
    summary jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.proxy_predictions
    ADD CONSTRAINT proxy_predictions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.proxy_predictions
    ADD CONSTRAINT proxy_predictions_run_id_fkey
    FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;

-- 报告快照表
CREATE TABLE IF NOT EXISTS public.report_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_id uuid NOT NULL,
    report_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.report_snapshots
    ADD CONSTRAINT report_snapshots_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.report_snapshots
    ADD CONSTRAINT report_snapshots_run_id_fkey
    FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;

-- 知网反馈表
CREATE TABLE IF NOT EXISTS public.cnki_feedback (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    predicted_run_id uuid,
    cnki_dup_percent double precision,
    cnki_aigc_percent double precision,
    report_date date,
    evidence_path text,
    notes text,
    verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.cnki_feedback
    ADD CONSTRAINT cnki_feedback_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.cnki_feedback
    ADD CONSTRAINT cnki_feedback_document_id_fkey
    FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

-- 模型注册表
CREATE TABLE IF NOT EXISTS public.model_registry (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    model_type character varying(80) NOT NULL,
    version character varying(200) NOT NULL,
    scene_key character varying(100),
    artifact_path text,
    is_active boolean DEFAULT false NOT NULL,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.model_registry
    ADD CONSTRAINT model_registry_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.model_registry
    ADD CONSTRAINT model_registry_version_key UNIQUE (version);
