CREATE TABLE IF NOT EXISTS public.app_users (
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

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_email_key UNIQUE (email);

CREATE TABLE IF NOT EXISTS public.user_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone
);

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_token_hash_key UNIQUE (token_hash);

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS public.user_document_access (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    document_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_user_document_key UNIQUE (user_id, document_id);

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_document_access
    ADD CONSTRAINT user_document_access_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS public.billing_orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    order_no character varying(80) NOT NULL,
    package_code character varying(50) NOT NULL,
    credits integer NOT NULL,
    amount_cents integer NOT NULL,
    status character varying(30) NOT NULL,
    provider character varying(50) DEFAULT 'mock'::character varying NOT NULL,
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT billing_orders_amount_cents_check CHECK ((amount_cents >= 0)),
    CONSTRAINT billing_orders_credits_check CHECK ((credits >= 0))
);

ALTER TABLE ONLY public.billing_orders
    ADD CONSTRAINT billing_orders_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_orders
    ADD CONSTRAINT billing_orders_order_no_key UNIQUE (order_no);

ALTER TABLE ONLY public.billing_orders
    ADD CONSTRAINT billing_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS public.credit_ledger (
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

ALTER TABLE ONLY public.credit_ledger
    ADD CONSTRAINT credit_ledger_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.credit_ledger
    ADD CONSTRAINT credit_ledger_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS public.analysis_tasks (
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

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.analysis_tasks
    ADD CONSTRAINT analysis_tasks_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.analysis_runs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_user_document_access_document_id ON public.user_document_access USING btree (document_id);
CREATE INDEX IF NOT EXISTS idx_user_document_access_user_id ON public.user_document_access USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_billing_orders_user_id ON public.billing_orders USING btree (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user_id ON public.credit_ledger USING btree (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_document_id ON public.analysis_tasks USING btree (document_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_user_id ON public.analysis_tasks USING btree (user_id, created_at DESC);
