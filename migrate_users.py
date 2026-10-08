from sqlalchemy import create_engine, text

cs = 'postgresql+psycopg2://postgres.ovapetxhquabhjmmrhaq:kanupsharma123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres'
engine = create_engine(cs)

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE public.users 
        ADD COLUMN IF NOT EXISTS email TEXT,
        ADD COLUMN IF NOT EXISTS college TEXT,
        ADD COLUMN IF NOT EXISTS target_study TEXT,
        ADD COLUMN IF NOT EXISTS verification_code TEXT,
        ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
    """))
    conn.execute(text("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;"))
    conn.execute(text('DROP POLICY IF EXISTS "Allow public all users" ON public.users;'))
    conn.execute(text('CREATE POLICY "Allow public all users" ON public.users FOR ALL USING (true) WITH CHECK (true);'))
    conn.commit()

print("Successfully updated public.users table in Supabase!")
