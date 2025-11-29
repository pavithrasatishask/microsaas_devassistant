-- Repositories table
CREATE TABLE repositories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    github_url TEXT NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    local_path TEXT,
    last_indexed TIMESTAMP WITH TIME ZONE,
    structure_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations table
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT REFERENCES repositories(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Impact analyses table
CREATE TABLE impact_analyses (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES conversations(id),
    request_type VARCHAR(100),
    request_description TEXT,
    affected_files JSONB,
    affected_features JSONB,
    risk_level VARCHAR(50) CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    warnings JSONB,
    recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Code changes table
CREATE TABLE code_changes (
    id BIGSERIAL PRIMARY KEY,
    analysis_id BIGINT REFERENCES impact_analyses(id),
    file_path TEXT NOT NULL,
    original_code TEXT,
    new_code TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'applied')),
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_repositories_name ON repositories(name);
CREATE INDEX idx_conversations_repo_id ON conversations(repo_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_impact_analyses_conversation_id ON impact_analyses(conversation_id);
CREATE INDEX idx_code_changes_analysis_id ON code_changes(analysis_id);

