-- Enable Supabase Realtime on reports table so postgres_changes subscriptions fire
ALTER PUBLICATION supabase_realtime ADD TABLE reports;
