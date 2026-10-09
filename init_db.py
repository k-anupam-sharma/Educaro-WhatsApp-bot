from sqlalchemy import create_engine, text

cs = 'postgresql+psycopg2://postgres.ovapetxhquabhjmmrhaq:kanupsharma123@aws-0-ap-south-1.pooler.supabase.com:5432/postgres'
engine = create_engine(cs)

queries = [
    """
    CREATE TABLE IF NOT EXISTS public.chat_history (
        id BIGSERIAL PRIMARY KEY,
        user_phone TEXT,
        user_message TEXT,
        ai_response TEXT,
        image_url TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    ALTER TABLE public.chat_history ADD COLUMN IF NOT EXISTS image_url TEXT;
    """,
    "ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;",
    'DROP POLICY IF EXISTS "Allow public insert" ON public.chat_history;',
    'CREATE POLICY "Allow public insert" ON public.chat_history FOR INSERT WITH CHECK (true);',
    'DROP POLICY IF EXISTS "Allow public select" ON public.chat_history;',
    'CREATE POLICY "Allow public select" ON public.chat_history FOR SELECT USING (true);',
    """
    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS extra_facts JSONB DEFAULT '{}'::jsonb;
    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS notes TEXT;
    """,
    """
    CREATE TABLE IF NOT EXISTS public.user_facts (
        id BIGSERIAL PRIMARY KEY,
        user_phone TEXT NOT NULL,
        fact_key TEXT NOT NULL,
        fact_value TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(user_phone, fact_key)
    );
    ALTER TABLE public.user_facts ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Allow public all" ON public.user_facts;
    CREATE POLICY "Allow public all" ON public.user_facts FOR ALL USING (true) WITH CHECK (true);
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'storage' AND tablename = 'objects') THEN
            DROP POLICY IF EXISTS "Allow public uploads to chat_media" ON storage.objects;
            CREATE POLICY "Allow public uploads to chat_media" ON storage.objects
                FOR INSERT WITH CHECK (bucket_id = 'chat_media');
            DROP POLICY IF EXISTS "Allow public select from chat_media" ON storage.objects;
            CREATE POLICY "Allow public select from chat_media" ON storage.objects
                FOR SELECT USING (bucket_id = 'chat_media');
        END IF;
    END
    $$;
    """
]

with engine.connect() as conn:
    for q in queries:
        conn.execute(text(q))
    conn.commit()

print("Successfully configured chat_history, users extra_facts, and user_facts in Supabase!")

