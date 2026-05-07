--
-- PostgreSQL database dump
--

\restrict YMZbvVXdLHq6CVzjDHCo0UiIdJoIsZgencO6FFGFrnkoPaYvNs1iCOJRtCDVFS2

-- Dumped from database version 17.9
-- Dumped by pg_dump version 17.9

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analysis_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_type character varying(30) NOT NULL,
    provider character varying(50) DEFAULT 'local'::character varying NOT NULL,
    provider_version character varying(100),
    status character varying(30) DEFAULT 'queued'::character varying NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: analysis_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analysis_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    document_id uuid NOT NULL,
    run_id uuid,
    task_type character varying(30) DEFAULT 'analysis'::character varying NOT NULL,
    status character varying(30) DEFAULT 'queued'::character varying NOT NULL,
    progress integer DEFAULT 0 NOT NULL,
    error_message text,
    result_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    CONSTRAINT analysis_tasks_progress_check CHECK (((progress >= 0) AND (progress <= 100)))
);


--
-- Name: app_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    display_name character varying(120),
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
    credits_balance integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT app_users_credits_balance_check CHECK ((credits_balance >= 0))
);


--
-- Name: billing_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    action character varying(100) NOT NULL,
    resource_type character varying(50),
    resource_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: billing_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.billing_orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    order_no character varying(80) NOT NULL,
    package_code character varying(50) NOT NULL,
    credits integer NOT NULL,
    amount_cents integer NOT NULL,
    status character varying(30) NOT NULL,
    provider character varying(50) DEFAULT 'mock'::character varying NOT NULL,
    payment_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    provider_trade_no character varying(120),
    notified_at timestamp with time zone,
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT billing_orders_amount_cents_check CHECK ((amount_cents >= 0)),
    CONSTRAINT billing_orders_credits_check CHECK ((credits >= 0))
);


--
-- Name: cnki_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cnki_feedback (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    predicted_run_id uuid,
    cnki_dup_percent numeric(6,2),
    cnki_aigc_percent numeric(6,2),
    report_date date,
    evidence_path text,
    notes text,
    verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT cnki_feedback_cnki_aigc_percent_check CHECK (((cnki_aigc_percent IS NULL) OR ((cnki_aigc_percent >= (0)::numeric) AND (cnki_aigc_percent <= (100)::numeric)))),
    CONSTRAINT cnki_feedback_cnki_dup_percent_check CHECK (((cnki_dup_percent IS NULL) OR ((cnki_dup_percent >= (0)::numeric) AND (cnki_dup_percent <= (100)::numeric))))
);


--
-- Name: credit_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_ledger (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    change_amount integer NOT NULL,
    balance_after integer NOT NULL,
    source_type character varying(50) NOT NULL,
    source_id uuid,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT credit_ledger_balance_after_check CHECK ((balance_after >= 0))
);


--
-- Name: document_sections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_sections (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    section_index integer NOT NULL,
    paragraph_index integer,
    section_type character varying(50),
    section_title character varying(255),
    text_preview character varying(500),
    content text NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    embedding public.vector(768),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT document_sections_char_count_check CHECK ((char_count >= 0)),
    CONSTRAINT document_sections_paragraph_index_check CHECK (((paragraph_index IS NULL) OR (paragraph_index >= 0))),
    CONSTRAINT document_sections_section_index_check CHECK ((section_index >= 0)),
    CONSTRAINT document_sections_section_type_check CHECK (((section_type IS NULL) OR ((section_type)::text = ANY ((ARRAY['abstract'::character varying, 'introduction'::character varying, 'review'::character varying, 'method'::character varying, 'result'::character varying, 'discussion'::character varying, 'conclusion'::character varying, 'references'::character varying, 'acknowledgement'::character varying, 'body'::character varying, 'other'::character varying])::text[]))))
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying(255),
    filename character varying(255) NOT NULL,
    subject character varying(100),
    degree_level character varying(50),
    language character varying(20) DEFAULT 'zh-CN'::character varying NOT NULL,
    doc_hash character varying(64) NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    section_count integer DEFAULT 0 NOT NULL,
    status character varying(30) DEFAULT 'queued'::character varying NOT NULL,
    source_type character varying(30) DEFAULT 'upload'::character varying NOT NULL,
    original_file_path text,
    cleaned_text_path text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    origin_document_id uuid
);


--
-- Name: model_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_registry (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    model_name character varying(100) NOT NULL,
    model_type character varying(30) NOT NULL,
    version character varying(100) NOT NULL,
    scene_key character varying(100),
    is_active boolean DEFAULT false NOT NULL,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL,
    artifact_path text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT model_registry_model_type_check CHECK (((model_type)::text = ANY ((ARRAY['cnki_dup_proxy'::character varying, 'cnki_aigc_proxy'::character varying, 'local_aigc'::character varying, 'local_dup'::character varying])::text[])))
);


--
-- Name: provider_payloads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_payloads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    provider character varying(50) NOT NULL,
    payload_type character varying(30) NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT provider_payloads_payload_type_check CHECK (((payload_type)::text = ANY ((ARRAY['request'::character varying, 'response'::character varying, 'normalized'::character varying])::text[]))),
    CONSTRAINT provider_payloads_provider_check CHECK (((provider)::text = ANY ((ARRAY['local'::character varying, 'wanfang'::character varying, 'vip'::character varying, 'turnitin'::character varying, 'manual'::character varying])::text[])))
);


--
-- Name: proxy_predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxy_predictions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_id uuid NOT NULL,
    model_version character varying(100) NOT NULL,
    scene_key character varying(100),
    predicted_cnki_dup numeric(6,4),
    predicted_cnki_dup_low numeric(6,4),
    predicted_cnki_dup_high numeric(6,4),
    predicted_cnki_aigc numeric(6,4),
    predicted_cnki_aigc_low numeric(6,4),
    predicted_cnki_aigc_high numeric(6,4),
    confidence numeric(6,4),
    summary jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT proxy_predictions_confidence_check CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT proxy_predictions_predicted_cnki_aigc_check CHECK (((predicted_cnki_aigc IS NULL) OR ((predicted_cnki_aigc >= (0)::numeric) AND (predicted_cnki_aigc <= (1)::numeric)))),
    CONSTRAINT proxy_predictions_predicted_cnki_aigc_high_check CHECK (((predicted_cnki_aigc_high IS NULL) OR ((predicted_cnki_aigc_high >= (0)::numeric) AND (predicted_cnki_aigc_high <= (1)::numeric)))),
    CONSTRAINT proxy_predictions_predicted_cnki_aigc_low_check CHECK (((predicted_cnki_aigc_low IS NULL) OR ((predicted_cnki_aigc_low >= (0)::numeric) AND (predicted_cnki_aigc_low <= (1)::numeric)))),
    CONSTRAINT proxy_predictions_predicted_cnki_dup_check CHECK (((predicted_cnki_dup IS NULL) OR ((predicted_cnki_dup >= (0)::numeric) AND (predicted_cnki_dup <= (1)::numeric)))),
    CONSTRAINT proxy_predictions_predicted_cnki_dup_high_check CHECK (((predicted_cnki_dup_high IS NULL) OR ((predicted_cnki_dup_high >= (0)::numeric) AND (predicted_cnki_dup_high <= (1)::numeric)))),
    CONSTRAINT proxy_predictions_predicted_cnki_dup_low_check CHECK (((predicted_cnki_dup_low IS NULL) OR ((predicted_cnki_dup_low >= (0)::numeric) AND (predicted_cnki_dup_low <= (1)::numeric))))
);


--
-- Name: report_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_id uuid NOT NULL,
    report_json jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: section_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.section_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    document_section_id uuid NOT NULL,
    score_type character varying(30) NOT NULL,
    raw_score numeric(6,4),
    normalized_score numeric(6,4),
    risk_level character varying(20),
    reasons jsonb DEFAULT '[]'::jsonb NOT NULL,
    signals jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT section_scores_normalized_score_check CHECK (((normalized_score IS NULL) OR ((normalized_score >= (0)::numeric) AND (normalized_score <= (1)::numeric)))),
    CONSTRAINT section_scores_raw_score_check CHECK (((raw_score IS NULL) OR ((raw_score >= (0)::numeric) AND (raw_score <= (1)::numeric)))),
    CONSTRAINT section_scores_risk_level_check CHECK (((risk_level IS NULL) OR ((risk_level)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying])::text[])))),
    CONSTRAINT section_scores_score_type_check CHECK (((score_type)::text = ANY ((ARRAY['aigc'::character varying, 'duplication'::character varying])::text[])))
);


--
-- Name: similarity_matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.similarity_matches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    document_section_id uuid NOT NULL,
    matched_source character varying(255),
    matched_title character varying(500),
    matched_snippet text,
    similarity_score numeric(6,4) NOT NULL,
    overlap_chars integer DEFAULT 0 NOT NULL,
    match_type character varying(30),
    source_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT similarity_matches_match_type_check CHECK (((match_type IS NULL) OR ((match_type)::text = ANY ((ARRAY['exact'::character varying, 'semantic'::character varying, 'paraphrase'::character varying])::text[])))),
    CONSTRAINT similarity_matches_overlap_chars_check CHECK ((overlap_chars >= 0)),
    CONSTRAINT similarity_matches_similarity_score_check CHECK (((similarity_score >= (0)::numeric) AND (similarity_score <= (1)::numeric)))
);


--
-- Name: user_document_access; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_document_access (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    document_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone
);


--
-- Name: analysis_runs analysis_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_runs
    ADD CONSTRAINT analysis_runs_pkey PRIMARY KEY (id);


--
-- Name: analysis_tasks analysis_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: app_users app_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_email_key UNIQUE (email);


--
-- Name: app_users app_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (id);


--
-- Name: billing_orders billing_orders_order_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing_orders
    ADD CONSTRAINT billing_orders_order_no_key UNIQUE (order_no);


--
-- Name: billing_orders billing_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing_orders
    ADD CONSTRAINT billing_orders_pkey PRIMARY KEY (id);


--
-- Name: cnki_feedback cnki_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cnki_feedback
    ADD CONSTRAINT cnki_feedback_pkey PRIMARY KEY (id);


--
-- Name: credit_ledger credit_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_ledger
    ADD CONSTRAINT credit_ledger_pkey PRIMARY KEY (id);


--
-- Name: document_sections document_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_sections
    ADD CONSTRAINT document_sections_pkey PRIMARY KEY (id);


--
-- Name: documents documents_doc_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_doc_hash_key UNIQUE (doc_hash);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: model_registry model_registry_model_name_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_registry
    ADD CONSTRAINT model_registry_model_name_version_key UNIQUE (model_name, version);


--
-- Name: model_registry model_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_registry
    ADD CONSTRAINT model_registry_pkey PRIMARY KEY (id);


--
-- Name: provider_payloads provider_payloads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_payloads
    ADD CONSTRAINT provider_payloads_pkey PRIMARY KEY (id);


--
-- Name: proxy_predictions proxy_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_predictions
    ADD CONSTRAINT proxy_predictions_pkey PRIMARY KEY (id);


--
-- Name: report_snapshots report_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_snapshots
    ADD CONSTRAINT report_snapshots_pkey PRIMARY KEY (id);


--
-- Name: section_scores section_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_pkey PRIMARY KEY (id);


--
-- Name: section_scores section_scores_run_id_document_section_id_score_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_run_id_document_section_id_score_type_key UNIQUE (run_id, document_section_id, score_type);


--
-- Name: similarity_matches similarity_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.similarity_matches
    ADD CONSTRAINT similarity_matches_pkey PRIMARY KEY (id);


--
-- Name: user_document_access user_document_access_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_pkey PRIMARY KEY (id);


--
-- Name: user_document_access user_document_access_user_document_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_user_document_key UNIQUE (user_id, document_id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: idx_analysis_tasks_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_tasks_document_id ON public.analysis_tasks USING btree (document_id, created_at DESC);


--
-- Name: idx_analysis_tasks_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_tasks_user_id ON public.analysis_tasks USING btree (user_id, created_at DESC);


--
-- Name: idx_billing_orders_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_billing_orders_user_id ON public.billing_orders USING btree (user_id, created_at DESC);


--
-- Name: idx_cnki_feedback_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cnki_feedback_document_id ON public.cnki_feedback USING btree (document_id);


--
-- Name: idx_cnki_feedback_report_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cnki_feedback_report_date ON public.cnki_feedback USING btree (report_date DESC);


--
-- Name: idx_cnki_feedback_verified; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cnki_feedback_verified ON public.cnki_feedback USING btree (verified);


--
-- Name: idx_credit_ledger_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_ledger_user_id ON public.credit_ledger USING btree (user_id, created_at DESC);


--
-- Name: idx_documents_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_created_at ON public.documents USING btree (created_at DESC);


--
-- Name: idx_documents_origin_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_origin_document_id ON public.documents USING btree (origin_document_id);


--
-- Name: idx_documents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_status ON public.documents USING btree (status);


--
-- Name: idx_documents_subject_degree; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_subject_degree ON public.documents USING btree (subject, degree_level);


--
-- Name: idx_model_registry_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_model_registry_active ON public.model_registry USING btree (is_active);


--
-- Name: idx_model_registry_type_scene; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_model_registry_type_scene ON public.model_registry USING btree (model_type, scene_key);


--
-- Name: idx_provider_payloads_provider_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_provider_payloads_provider_type ON public.provider_payloads USING btree (provider, payload_type);


--
-- Name: idx_provider_payloads_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_provider_payloads_run_id ON public.provider_payloads USING btree (run_id);


--
-- Name: idx_proxy_predictions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proxy_predictions_created_at ON public.proxy_predictions USING btree (created_at DESC);


--
-- Name: idx_proxy_predictions_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proxy_predictions_document_id ON public.proxy_predictions USING btree (document_id);


--
-- Name: idx_proxy_predictions_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proxy_predictions_run_id ON public.proxy_predictions USING btree (run_id);


--
-- Name: idx_proxy_predictions_scene_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proxy_predictions_scene_key ON public.proxy_predictions USING btree (scene_key);


--
-- Name: idx_report_snapshots_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_report_snapshots_created_at ON public.report_snapshots USING btree (created_at DESC);


--
-- Name: idx_report_snapshots_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_report_snapshots_document_id ON public.report_snapshots USING btree (document_id);


--
-- Name: idx_report_snapshots_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_report_snapshots_run_id ON public.report_snapshots USING btree (run_id);


--
-- Name: idx_runs_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_document_id ON public.analysis_runs USING btree (document_id);


--
-- Name: idx_runs_provider_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_provider_type ON public.analysis_runs USING btree (provider, run_type);


--
-- Name: idx_runs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_status ON public.analysis_runs USING btree (status);


--
-- Name: idx_section_scores_risk; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_section_scores_risk ON public.section_scores USING btree (risk_level);


--
-- Name: idx_section_scores_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_section_scores_run_id ON public.section_scores USING btree (run_id);


--
-- Name: idx_section_scores_section_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_section_scores_section_id ON public.section_scores USING btree (document_section_id);


--
-- Name: idx_section_scores_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_section_scores_type ON public.section_scores USING btree (score_type);


--
-- Name: idx_sections_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_document_id ON public.document_sections USING btree (document_id);


--
-- Name: idx_sections_document_section_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_document_section_index ON public.document_sections USING btree (document_id, section_index);


--
-- Name: idx_sections_section_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_section_type ON public.document_sections USING btree (section_type);


--
-- Name: idx_similarity_matches_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_similarity_matches_run_id ON public.similarity_matches USING btree (run_id);


--
-- Name: idx_similarity_matches_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_similarity_matches_score ON public.similarity_matches USING btree (similarity_score DESC);


--
-- Name: idx_similarity_matches_section_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_similarity_matches_section_id ON public.similarity_matches USING btree (document_section_id);


--
-- Name: idx_user_document_access_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_document_access_document_id ON public.user_document_access USING btree (document_id);


--
-- Name: idx_user_document_access_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_document_access_user_id ON public.user_document_access USING btree (user_id);


--
-- Name: idx_document_sections_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_sections_embedding_hnsw ON public.document_sections USING hnsw (embedding vector_cosine_ops);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE SET NULL;


--
-- Name: analysis_runs analysis_runs_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_runs
    ADD CONSTRAINT analysis_runs_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: analysis_tasks analysis_tasks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: analysis_tasks analysis_tasks_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE SET NULL;


--
-- Name: analysis_tasks analysis_tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE SET NULL;


--
-- Name: billing_orders billing_orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing_orders
    ADD CONSTRAINT billing_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- Name: cnki_feedback cnki_feedback_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cnki_feedback
    ADD CONSTRAINT cnki_feedback_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: cnki_feedback cnki_feedback_predicted_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cnki_feedback
    ADD CONSTRAINT cnki_feedback_predicted_run_id_fkey FOREIGN KEY (predicted_run_id) REFERENCES public.analysis_runs(id) ON DELETE SET NULL;


--
-- Name: credit_ledger credit_ledger_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_ledger
    ADD CONSTRAINT credit_ledger_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- Name: document_sections document_sections_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_sections
    ADD CONSTRAINT document_sections_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: documents documents_origin_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_origin_document_id_fkey FOREIGN KEY (origin_document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: provider_payloads provider_payloads_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_payloads
    ADD CONSTRAINT provider_payloads_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;


--
-- Name: proxy_predictions proxy_predictions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_predictions
    ADD CONSTRAINT proxy_predictions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: proxy_predictions proxy_predictions_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_predictions
    ADD CONSTRAINT proxy_predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;


--
-- Name: report_snapshots report_snapshots_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_snapshots
    ADD CONSTRAINT report_snapshots_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: report_snapshots report_snapshots_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_snapshots
    ADD CONSTRAINT report_snapshots_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;


--
-- Name: section_scores section_scores_document_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_document_section_id_fkey FOREIGN KEY (document_section_id) REFERENCES public.document_sections(id) ON DELETE CASCADE;


--
-- Name: section_scores section_scores_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_scores
    ADD CONSTRAINT section_scores_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;


--
-- Name: similarity_matches similarity_matches_document_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.similarity_matches
    ADD CONSTRAINT similarity_matches_document_section_id_fkey FOREIGN KEY (document_section_id) REFERENCES public.document_sections(id) ON DELETE CASCADE;


--
-- Name: similarity_matches similarity_matches_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.similarity_matches
    ADD CONSTRAINT similarity_matches_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;


--
-- Name: user_document_access user_document_access_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: user_document_access user_document_access_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict YMZbvVXdLHq6CVzjDHCo0UiIdJoIsZgencO6FFGFrnkoPaYvNs1iCOJRtCDVFS2
