-- Bring existing deployments up to the report-mode/document-block schema.
-- Idempotent by design so it can be applied to old local databases safely.

ALTER TABLE public.analysis_runs
    ADD COLUMN IF NOT EXISTS mode character varying(20) DEFAULT 'estimate'::character varying;

CREATE TABLE IF NOT EXISTS public.document_blocks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    block_id character varying(64) NOT NULL,
    block_type character varying(30) NOT NULL,
    text text NOT NULL,
    html text,
    source_type character varying(20) NOT NULL,
    source_map jsonb DEFAULT '{}'::jsonb,
    section_index integer,
    paragraph_index integer,
    section_title character varying(255),
    section_type character varying(50),
    char_count integer DEFAULT 0 NOT NULL,
    display_order integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    risk_score float,
    report_risk jsonb,
    internal_risk jsonb,
    CONSTRAINT document_blocks_char_count_check CHECK (char_count >= 0),
    CONSTRAINT document_blocks_display_order_check CHECK (display_order >= 0),
    CONSTRAINT document_blocks_paragraph_index_check CHECK (paragraph_index IS NULL OR paragraph_index >= 0),
    CONSTRAINT document_blocks_section_index_check CHECK (section_index IS NULL OR section_index >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_document_blocks_doc_block
    ON public.document_blocks(document_id, block_id);
CREATE INDEX IF NOT EXISTS idx_document_blocks_doc_order
    ON public.document_blocks(document_id, display_order);

CREATE TABLE IF NOT EXISTS public.document_patches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_id uuid,
    block_id character varying(64) NOT NULL,
    old_text text NOT NULL,
    new_text text NOT NULL,
    source_map jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);

CREATE INDEX IF NOT EXISTS idx_document_patches_doc_block
    ON public.document_patches(document_id, block_id);
CREATE INDEX IF NOT EXISTS idx_document_patches_run
    ON public.document_patches(run_id);

CREATE TABLE IF NOT EXISTS public.cnki_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    run_id uuid,
    report_type character varying(30) NOT NULL,
    filename character varying(500),
    raw_format character varying(20),
    total_copy_ratio float,
    aigc_ratio float,
    generated_at timestamp with time zone,
    parsed_at timestamp with time zone DEFAULT now(),
    raw_data jsonb DEFAULT '{}'::jsonb,
    status character varying(20) DEFAULT 'parsed'::character varying
);

CREATE TABLE IF NOT EXISTS public.cnki_report_spans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    report_id uuid NOT NULL,
    span_id character varying(64) NOT NULL,
    text text NOT NULL,
    risk_type character varying(30) NOT NULL,
    risk_level character varying(20) NOT NULL,
    similarity float,
    aigc_score float,
    matched_source text,
    page_number integer,
    raw_meta jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.block_report_mappings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    block_id character varying(64) NOT NULL,
    span_id character varying(64) NOT NULL,
    report_id uuid NOT NULL,
    match_method character varying(20) NOT NULL,
    match_confidence float NOT NULL,
    matched_text text,
    created_at timestamp with time zone DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'document_blocks_pkey'
    ) THEN
        ALTER TABLE ONLY public.document_blocks ADD CONSTRAINT document_blocks_pkey PRIMARY KEY (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'document_blocks_document_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.document_blocks
            ADD CONSTRAINT document_blocks_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'document_patches_pkey'
    ) THEN
        ALTER TABLE ONLY public.document_patches ADD CONSTRAINT document_patches_pkey PRIMARY KEY (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'document_patches_document_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.document_patches
            ADD CONSTRAINT document_patches_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'document_patches_run_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.document_patches
            ADD CONSTRAINT document_patches_run_id_fkey
            FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cnki_reports_pkey'
    ) THEN
        ALTER TABLE ONLY public.cnki_reports ADD CONSTRAINT cnki_reports_pkey PRIMARY KEY (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cnki_reports_document_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.cnki_reports
            ADD CONSTRAINT cnki_reports_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cnki_reports_run_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.cnki_reports
            ADD CONSTRAINT cnki_reports_run_id_fkey
            FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cnki_report_spans_pkey'
    ) THEN
        ALTER TABLE ONLY public.cnki_report_spans ADD CONSTRAINT cnki_report_spans_pkey PRIMARY KEY (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cnki_report_spans_report_id_span_id_key'
    ) THEN
        ALTER TABLE ONLY public.cnki_report_spans
            ADD CONSTRAINT cnki_report_spans_report_id_span_id_key UNIQUE (report_id, span_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cnki_report_spans_report_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.cnki_report_spans
            ADD CONSTRAINT cnki_report_spans_report_id_fkey
            FOREIGN KEY (report_id) REFERENCES public.cnki_reports(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'block_report_mappings_pkey'
    ) THEN
        ALTER TABLE ONLY public.block_report_mappings ADD CONSTRAINT block_report_mappings_pkey PRIMARY KEY (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'block_report_mappings_doc_block_span_key'
    ) THEN
        ALTER TABLE ONLY public.block_report_mappings
            ADD CONSTRAINT block_report_mappings_doc_block_span_key UNIQUE (document_id, block_id, span_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'block_report_mappings_document_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.block_report_mappings
            ADD CONSTRAINT block_report_mappings_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'block_report_mappings_report_id_fkey'
    ) THEN
        ALTER TABLE ONLY public.block_report_mappings
            ADD CONSTRAINT block_report_mappings_report_id_fkey
            FOREIGN KEY (report_id) REFERENCES public.cnki_reports(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_cnki_reports_doc ON public.cnki_reports(document_id);
CREATE INDEX IF NOT EXISTS idx_cnki_reports_run ON public.cnki_reports(run_id);
CREATE INDEX IF NOT EXISTS idx_cnki_spans_report ON public.cnki_report_spans(report_id);
CREATE INDEX IF NOT EXISTS idx_cnki_spans_risk ON public.cnki_report_spans(report_id, risk_level);
CREATE INDEX IF NOT EXISTS idx_block_mappings_doc ON public.block_report_mappings(document_id, block_id);
CREATE INDEX IF NOT EXISTS idx_block_mappings_span ON public.block_report_mappings(report_id, span_id);
