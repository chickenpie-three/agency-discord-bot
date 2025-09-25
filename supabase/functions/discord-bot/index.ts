// Supabase Edge Function for STAFFVIRTUAL Discord Bot
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_ANON_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Health check endpoint
    if (req.url.includes('/health')) {
      return new Response(
        JSON.stringify({ 
          status: 'healthy', 
          timestamp: new Date().toISOString(),
          service: 'STAFFVIRTUAL Discord Bot'
        }),
        { 
          headers: { 
            ...corsHeaders, 
            'Content-Type': 'application/json' 
          } 
        }
      )
    }

    // Knowledge base endpoints
    if (req.method === 'POST' && req.url.includes('/knowledge')) {
      const body = await req.json()
      
      // Store knowledge in Supabase
      const { data, error } = await supabase
        .from('knowledge_base')
        .insert([
          {
            source_type: body.type,
            source_url: body.url,
            title: body.title,
            content: body.content,
            metadata: body.metadata,
            created_at: new Date().toISOString()
          }
        ])

      if (error) {
        return new Response(
          JSON.stringify({ error: error.message }),
          { 
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      return new Response(
        JSON.stringify({ success: true, data }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Search knowledge base
    if (req.method === 'GET' && req.url.includes('/knowledge/search')) {
      const url = new URL(req.url)
      const query = url.searchParams.get('q')

      if (!query) {
        return new Response(
          JSON.stringify({ error: 'Query parameter required' }),
          { 
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      // Search in knowledge base
      const { data, error } = await supabase
        .from('knowledge_base')
        .select('*')
        .textSearch('content', query)
        .limit(10)

      if (error) {
        return new Response(
          JSON.stringify({ error: error.message }),
          { 
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      return new Response(
        JSON.stringify({ results: data }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Default response
    return new Response(
      JSON.stringify({ 
        message: 'STAFFVIRTUAL Discord Bot API',
        version: '1.0.0',
        endpoints: ['/health', '/knowledge', '/knowledge/search']
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})
