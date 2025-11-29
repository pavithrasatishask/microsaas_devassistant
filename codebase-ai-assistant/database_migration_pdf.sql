-- Migration: Add PDF document support
-- Run this after the initial database_schema.sql

-- Add columns to repositories table
ALTER TABLE repositories 
ADD COLUMN IF NOT EXISTS documents_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS has_documents BOOLEAN DEFAULT FALSE;

-- Repository documents table
CREATE TABLE IF NOT EXISTS repository_documents (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT REFERENCES repositories(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'pdf' CHECK (document_type IN ('pdf', 'docx', 'txt')),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT,  -- Local filesystem path
    file_url TEXT,   -- If uploaded to Supabase Storage
    file_size BIGINT,  -- Size in bytes
    pages INTEGER,     -- Number of pages (for PDFs)
    extracted_text TEXT,  -- Full extracted text
    text_summary TEXT,    -- AI-generated summary
    metadata JSONB,      -- Additional metadata (author, title, etc.)
    processing_status VARCHAR(50) DEFAULT 'pending' 
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for repository_documents
CREATE INDEX IF NOT EXISTS idx_repository_documents_repo_id ON repository_documents(repo_id);
CREATE INDEX IF NOT EXISTS idx_repository_documents_status ON repository_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_repository_documents_type ON repository_documents(document_type);


