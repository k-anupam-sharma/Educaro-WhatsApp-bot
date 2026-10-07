from sqlalchemy import create_engine, text

cs = 'postgresql+psycopg2://postgres:kanupsharma123@db.ovapetxhquabhjmmrhaq.supabase.co:5432/postgres'
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

print("Successfully configured chat_history and storage policies in Supabase!")
