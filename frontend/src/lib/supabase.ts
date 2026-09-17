import { createClient } from "@supabase/supabase-js";

const env = (import.meta as unknown as { env?: Record<string, string> }).env || {};
const supabaseUrl = env.VITE_SUPABASE_URL || "https://demo.supabase.co";
const supabaseAnonKey = env.VITE_SUPABASE_ANON_KEY || "demo-anon-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
