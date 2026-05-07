ALTER TABLE public.billing_orders
    ADD COLUMN IF NOT EXISTS payment_payload jsonb DEFAULT '{}'::jsonb NOT NULL;

ALTER TABLE public.billing_orders
    ADD COLUMN IF NOT EXISTS provider_trade_no character varying(120);

ALTER TABLE public.billing_orders
    ADD COLUMN IF NOT EXISTS notified_at timestamp with time zone;
