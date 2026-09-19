-- =============================================================================
-- LexAI Simplifier — Phase 1 Database Schema
-- =============================================================================
-- Compatible with: PostgreSQL 14+ / Supabase
--
-- Tables:
--   documents       — uploaded legal documents
--   document_pages  — extracted text per page
--
-- To apply:
--   Supabase: Dashboard → SQL Editor → paste and run
--   Local:    psql -U postgres -d your_db -f schema.sql
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUM: document status
-- =============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_status') THEN
    CREATE TYPE document_status AS ENUM (
      'UPLOADED',
      'PROCESSING',
      'ANALYZED',
      'FAILED'
    );
  END IF;
END
$$;

-- =============================================================================
-- TABLE: documents
-- =============================================================================

CREATE TABLE IF NOT EXISTS documents (
  id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
  filename      VARCHAR(512)    NOT NULL,
  document_type VARCHAR(100)    NOT NULL,
  file_type     VARCHAR(10)     NOT NULL,       -- 'pdf' | 'txt'
  file_size     BIGINT          NOT NULL,        -- bytes
  status        document_status NOT NULL DEFAULT 'UPLOADED',
  created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
  BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX IF NOT EXISTS ix_documents_status     ON documents (status);
CREATE INDEX IF NOT EXISTS ix_documents_created_at ON documents (created_at DESC);

-- =============================================================================
-- TABLE: document_pages
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_pages (
  id           UUID     PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  UUID     NOT NULL
                        REFERENCES documents (id) ON DELETE CASCADE,
  page_number  INTEGER  NOT NULL,
  text         TEXT     NOT NULL DEFAULT '',
  char_start   BIGINT,          -- character offset in full document text
  char_end     BIGINT
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_document_pages_document_id  ON document_pages (document_id);
CREATE INDEX IF NOT EXISTS ix_document_pages_page_number  ON document_pages (page_number);

-- =============================================================================
-- TABLE: clauses
-- =============================================================================

CREATE TABLE IF NOT EXISTS clauses (
  id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id    UUID         NOT NULL
                              REFERENCES documents (id) ON DELETE CASCADE,
  section_number VARCHAR(100),
  section_title  VARCHAR(255),
  clause_text    TEXT         NOT NULL,
  risk_level     VARCHAR(10)  NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
  explanation    TEXT         NOT NULL,
  reason         TEXT         NOT NULL,
  page_number    INTEGER,
  char_start     BIGINT,
  char_end       BIGINT,
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for clauses
CREATE INDEX IF NOT EXISTS ix_clauses_document_id  ON clauses (document_id);
CREATE INDEX IF NOT EXISTS ix_clauses_risk_level   ON clauses (risk_level);
CREATE INDEX IF NOT EXISTS ix_clauses_page_number  ON clauses (page_number);

-- =============================================================================
-- TABLE: analysis_summaries
-- =============================================================================

CREATE TABLE IF NOT EXISTS analysis_summaries (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID         NOT NULL
                               REFERENCES documents (id) ON DELETE CASCADE,
  total_clauses   INTEGER      NOT NULL DEFAULT 0,
  high_count      INTEGER      NOT NULL DEFAULT 0,
  medium_count    INTEGER      NOT NULL DEFAULT 0,
  low_count       INTEGER      NOT NULL DEFAULT 0,
  overall_summary TEXT         NOT NULL DEFAULT '',
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_analysis_summaries_document_id UNIQUE (document_id)
);

-- Index for analysis_summaries
CREATE INDEX IF NOT EXISTS ix_analysis_summaries_document_id ON analysis_summaries (document_id);

-- =============================================================================
-- TABLE: document_chunks
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id   UUID         NOT NULL
                             REFERENCES documents (id) ON DELETE CASCADE,
  clause_id     UUID         REFERENCES clauses (id) ON DELETE SET NULL,
  page_number   INTEGER,
  chunk_text    TEXT         NOT NULL,
  char_start    BIGINT,
  char_end      BIGINT,
  embedding     JSONB,       -- Vector representation stored as array
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for document_chunks
CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id  ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_clause_id    ON document_chunks (clause_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_page_number  ON document_chunks (page_number);

-- =============================================================================
-- TABLE: chat_sessions
-- =============================================================================

CREATE TABLE IF NOT EXISTS chat_sessions (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id   UUID         NOT NULL
                             REFERENCES documents (id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index for chat_sessions
CREATE INDEX IF NOT EXISTS ix_chat_sessions_document_id ON chat_sessions (document_id);

-- =============================================================================
-- TABLE: chat_messages
-- =============================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    UUID         NOT NULL
                             REFERENCES chat_sessions (id) ON DELETE CASCADE,
  role          VARCHAR(20)  NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  message       TEXT         NOT NULL,
  grounded      BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for chat_messages
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages (created_at);

-- =============================================================================
-- TABLE: chat_sources
-- =============================================================================

CREATE TABLE IF NOT EXISTS chat_sources (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id      UUID         NOT NULL
                               REFERENCES chat_messages (id) ON DELETE CASCADE,
  clause_id       UUID         REFERENCES clauses (id) ON DELETE SET NULL,
  page_number     INTEGER,
  relevance_score FLOAT,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index for chat_sources
CREATE INDEX IF NOT EXISTS ix_chat_sources_message_id ON chat_sources (message_id);

-- =============================================================================
-- TABLE: standard_contract_templates (SRS-S02)
-- =============================================================================

CREATE TABLE IF NOT EXISTS standard_contract_templates (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  document_type VARCHAR(100) NOT NULL UNIQUE, -- 'Rental Agreement', 'Freelance Contract', 'Terms of Service', 'Other'
  name          VARCHAR(255) NOT NULL,
  description   TEXT         NOT NULL DEFAULT '',
  version       VARCHAR(20)  NOT NULL DEFAULT '1.0',
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at for standard_contract_templates
DROP TRIGGER IF EXISTS trg_standard_contract_templates_updated_at ON standard_contract_templates;
CREATE TRIGGER trg_standard_contract_templates_updated_at
  BEFORE UPDATE ON standard_contract_templates
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Index for standard_contract_templates
CREATE INDEX IF NOT EXISTS ix_standard_templates_document_type ON standard_contract_templates (document_type);

-- =============================================================================
-- TABLE: standard_clauses (SRS-S02)
-- =============================================================================

CREATE TABLE IF NOT EXISTS standard_clauses (
  id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id    UUID         NOT NULL
                              REFERENCES standard_contract_templates (id) ON DELETE CASCADE,
  category       VARCHAR(100) NOT NULL, -- 'PAYMENT', 'TERMINATION', 'RENEWAL', 'LIABILITY', 'INDEMNITY', etc.
  title          VARCHAR(255) NOT NULL,
  benchmark_text TEXT         NOT NULL,
  description    TEXT         NOT NULL DEFAULT '',
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for standard_clauses
CREATE INDEX IF NOT EXISTS ix_standard_clauses_template_id ON standard_clauses (template_id);
CREATE INDEX IF NOT EXISTS ix_standard_clauses_category    ON standard_clauses (category);

-- =============================================================================
-- TABLE: clause_comparisons (SRS-S02)
-- =============================================================================

CREATE TABLE IF NOT EXISTS clause_comparisons (
  id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id        UUID         NOT NULL
                                  REFERENCES documents (id) ON DELETE CASCADE,
  clause_id          UUID         NOT NULL
                                  REFERENCES clauses (id) ON DELETE CASCADE,
  standard_clause_id UUID         REFERENCES standard_clauses (id) ON DELETE SET NULL,
  category           VARCHAR(100) NOT NULL,
  deviation_level    VARCHAR(10)  NOT NULL CHECK (deviation_level IN ('LOW', 'MEDIUM', 'HIGH')),
  similarity_score   FLOAT        NOT NULL DEFAULT 0.0,
  comparison_summary TEXT         NOT NULL DEFAULT '',
  differences        JSONB        NOT NULL DEFAULT '[]'::jsonb,
  created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for clause_comparisons
CREATE INDEX IF NOT EXISTS ix_clause_comparisons_document_id     ON clause_comparisons (document_id);
CREATE INDEX IF NOT EXISTS ix_clause_comparisons_clause_id       ON clause_comparisons (clause_id);
CREATE INDEX IF NOT EXISTS ix_clause_comparisons_standard_id     ON clause_comparisons (standard_clause_id);
CREATE INDEX IF NOT EXISTS ix_clause_comparisons_deviation_level ON clause_comparisons (deviation_level);

-- =============================================================================
-- Comments (documentation)
-- =============================================================================

COMMENT ON TABLE documents IS
  'Uploaded legal documents with processing status.';
COMMENT ON COLUMN documents.file_type IS
  'File extension without dot: pdf or txt.';
COMMENT ON COLUMN documents.status IS
  'Processing lifecycle: UPLOADED → PROCESSING → ANALYZED | FAILED.';

COMMENT ON TABLE document_pages IS
  'Text extracted from individual pages of a document.';
COMMENT ON COLUMN document_pages.char_start IS
  'Start character offset in the full concatenated document text.';
COMMENT ON COLUMN document_pages.char_end IS
  'End character offset in the full concatenated document text.';

COMMENT ON TABLE clauses IS
  'Extracted contractual clauses with risk analysis, explanation, and offsets.';
COMMENT ON COLUMN clauses.risk_level IS
  'Risk classification: LOW, MEDIUM, or HIGH.';

COMMENT ON TABLE analysis_summaries IS
  'Aggregated risk analysis counts and overall plain-language summary per document.';

COMMENT ON TABLE document_chunks IS
  'Section- and clause-aware document text chunks with embeddings for vector search.';

COMMENT ON TABLE chat_sessions IS
  'Conversational sessions scoped per uploaded contract.';

COMMENT ON TABLE chat_messages IS
  'Individual user and assistant messages with grounding verification.';

COMMENT ON TABLE chat_sources IS
  'Retrieved clause and page source citations supporting assistant answers.';

COMMENT ON TABLE standard_contract_templates IS
  'Standard contract archetype benchmarks (Rental, Freelance, Terms of Service, Other).';

COMMENT ON TABLE standard_clauses IS
  'Benchmark clause templates for comparison against uploaded contract clauses.';

COMMENT ON TABLE clause_comparisons IS
  'Evaluated deviation and differences between document clauses and standard benchmarks.';

