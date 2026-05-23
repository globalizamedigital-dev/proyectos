export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      leads: {
        Row: {
          city: string | null
          cnae: string | null
          data: Json
          decisor: string | null
          decisor_role: string | null
          dedup_key: string
          domain: string | null
          email_principal: string | null
          first_seen: string
          grade: string
          id: string
          last_seen: string
          nif: string | null
          outreach_status: string
          provincia: string | null
          razon_social: string | null
          score: number
          score_rationale: string | null
          sector: string | null
          sources_hit: string[]
          telefono: string | null
          tenant_id: string
        }
        Insert: {
          city?: string | null
          cnae?: string | null
          data?: Json
          decisor?: string | null
          decisor_role?: string | null
          dedup_key: string
          domain?: string | null
          email_principal?: string | null
          first_seen?: string
          grade?: string
          id?: string
          last_seen?: string
          nif?: string | null
          outreach_status?: string
          provincia?: string | null
          razon_social?: string | null
          score?: number
          score_rationale?: string | null
          sector?: string | null
          sources_hit?: string[]
          telefono?: string | null
          tenant_id: string
        }
        Update: {
          city?: string | null
          cnae?: string | null
          data?: Json
          decisor?: string | null
          decisor_role?: string | null
          dedup_key?: string
          domain?: string | null
          email_principal?: string | null
          first_seen?: string
          grade?: string
          id?: string
          last_seen?: string
          nif?: string | null
          outreach_status?: string
          provincia?: string | null
          razon_social?: string | null
          score?: number
          score_rationale?: string | null
          sector?: string | null
          sources_hit?: string[]
          telefono?: string | null
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "leads_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      leads_embeddings: {
        Row: {
          embedding: string
          lead_id: string
          model: string
          updated_at: string
        }
        Insert: {
          embedding: string
          lead_id: string
          model?: string
          updated_at?: string
        }
        Update: {
          embedding?: string
          lead_id?: string
          model?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "leads_embeddings_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: true
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
        ]
      }
      outreach_events: {
        Row: {
          channel: string
          created_at: string
          error_message: string | null
          event_type: string
          id: string
          lead_id: string
          meta: Json
          sequence_id: string | null
          skip_reason: string | null
          template_id: string | null
          tenant_id: string
        }
        Insert: {
          channel: string
          created_at?: string
          error_message?: string | null
          event_type: string
          id?: string
          lead_id: string
          meta?: Json
          sequence_id?: string | null
          skip_reason?: string | null
          template_id?: string | null
          tenant_id: string
        }
        Update: {
          channel?: string
          created_at?: string
          error_message?: string | null
          event_type?: string
          id?: string
          lead_id?: string
          meta?: Json
          sequence_id?: string | null
          skip_reason?: string | null
          template_id?: string | null
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "outreach_events_lead_id_fkey"
            columns: ["lead_id"]
            isOneToOne: false
            referencedRelation: "leads"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "outreach_events_sequence_id_fkey"
            columns: ["sequence_id"]
            isOneToOne: false
            referencedRelation: "outreach_sequences"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "outreach_events_template_id_fkey"
            columns: ["template_id"]
            isOneToOne: false
            referencedRelation: "outreach_templates"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "outreach_events_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      outreach_sequences: {
        Row: {
          created_at: string
          enabled: boolean
          id: string
          name: string
          slug: string
          steps: Json
          tenant_id: string
        }
        Insert: {
          created_at?: string
          enabled?: boolean
          id?: string
          name: string
          slug: string
          steps?: Json
          tenant_id: string
        }
        Update: {
          created_at?: string
          enabled?: boolean
          id?: string
          name?: string
          slug?: string
          steps?: Json
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "outreach_sequences_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      outreach_templates: {
        Row: {
          body: string
          channel: string
          created_at: string
          id: string
          name: string
          slug: string
          subject: string | null
          tenant_id: string
          updated_at: string
          variables: string[]
        }
        Insert: {
          body: string
          channel: string
          created_at?: string
          id?: string
          name: string
          slug: string
          subject?: string | null
          tenant_id: string
          updated_at?: string
          variables?: string[]
        }
        Update: {
          body?: string
          channel?: string
          created_at?: string
          id?: string
          name?: string
          slug?: string
          subject?: string | null
          tenant_id?: string
          updated_at?: string
          variables?: string[]
        }
        Relationships: [
          {
            foreignKeyName: "outreach_templates_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      suppression: {
        Row: {
          channel: string
          created_at: string
          identifier: string
          notes: string | null
          reason: string
          tenant_id: string
        }
        Insert: {
          channel: string
          created_at?: string
          identifier: string
          notes?: string | null
          reason: string
          tenant_id: string
        }
        Update: {
          channel?: string
          created_at?: string
          identifier?: string
          notes?: string | null
          reason?: string
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "suppression_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      tenant_members: {
        Row: {
          created_at: string
          role: string
          tenant_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          role?: string
          tenant_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          role?: string
          tenant_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "tenant_members_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      tenants: {
        Row: {
          created_at: string
          id: string
          name: string
          slug: string
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          slug: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          slug?: string
        }
        Relationships: []
      }
      usage_events: {
        Row: {
          cost_eur: number | null
          created_at: string
          free_tier_remaining_pct: number | null
          id: string
          meta: Json
          operation: string | null
          service: string
          tenant_id: string | null
          units: number
        }
        Insert: {
          cost_eur?: number | null
          created_at?: string
          free_tier_remaining_pct?: number | null
          id?: string
          meta?: Json
          operation?: string | null
          service: string
          tenant_id?: string | null
          units?: number
        }
        Update: {
          cost_eur?: number | null
          created_at?: string
          free_tier_remaining_pct?: number | null
          id?: string
          meta?: Json
          operation?: string | null
          service?: string
          tenant_id?: string | null
          units?: number
        }
        Relationships: [
          {
            foreignKeyName: "usage_events_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      current_user_tenants: { Args: never; Returns: string[] }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const

