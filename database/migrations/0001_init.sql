-- 0001_init.sql — initial schema for Report Validator / Account Violation Finder
-- Auto-generated from backend/models/*.py via SQLAlchemy metadata (see
-- backend for the source of truth). Provided for production deployments
-- that prefer explicit, reviewable DDL over create_all(); the app itself
-- runs Base.metadata.create_all() at startup for local/dev convenience.
-- Target: PostgreSQL (Supabase-compatible).

CREATE TYPE priority_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

CREATE TYPE case_status_enum AS ENUM ('NEW', 'COLLECTING_EVIDENCE', 'EVIDENCE_VALIDATED', 'UNDER_REVIEW', 'VIOLATION_CONFIRMED', 'REPORT_READY', 'SUBMITTED', 'ACKNOWLEDGED', 'ACTION_TAKEN', 'REJECTED', 'CLOSED');

CREATE TYPE evidence_type_enum AS ENUM ('SCREENSHOT', 'VIDEO', 'IMAGE', 'PUBLIC_POST', 'PUBLIC_COMMENT', 'PUBLIC_PROFILE', 'PUBLIC_URL', 'ARTICLE', 'ARCHIVE', 'DOCUMENT', 'API_RESPONSE', 'METADATA');

CREATE TYPE evidence_verification_status_enum AS ENUM ('PENDING', 'VERIFIED', 'FAILED', 'DUPLICATE');

CREATE TYPE violation_category_enum AS ENUM ('HARASSMENT', 'THREATS', 'VIOLENCE', 'HATE', 'SEXUAL_CONTENT', 'CHILD_SAFETY', 'FRAUD', 'IMPERSONATION', 'SPAM', 'SCAM', 'PHISHING', 'PRIVACY_VIOLATION', 'COPYRIGHT', 'TRADEMARK', 'MALWARE', 'ILLEGAL_CONTENT', 'SELF_HARM', 'PLATFORM_MANIPULATION', 'DECEPTIVE_PRACTICE', 'OTHER');

CREATE TYPE readiness_level_enum AS ENUM ('READY', 'NEEDS_REVIEW', 'INSUFFICIENT');

CREATE TYPE report_status_enum AS ENUM ('DRAFT', 'READY', 'SUBMITTED', 'ACKNOWLEDGED', 'REJECTED', 'ACTIONED', 'CLOSED');

CREATE TYPE review_queue_status_enum AS ENUM ('PENDING', 'APPROVED', 'NEEDS_MORE_EVIDENCE', 'REJECTED', 'RETURNED');

CREATE TYPE review_action_enum AS ENUM ('APPROVE', 'REQUEST_MORE_EVIDENCE', 'REJECT', 'RETURN_TO_OPERATOR');

CREATE TYPE role_enum AS ENUM ('ADMIN', 'ANALYST', 'REVIEWER', 'AUDITOR', 'VIEWER');

CREATE TYPE assessment_category_enum AS ENUM ('HARASSMENT', 'THREATS', 'VIOLENCE', 'HATE', 'SEXUAL_CONTENT', 'CHILD_SAFETY', 'FRAUD', 'IMPERSONATION', 'SPAM', 'SCAM', 'PHISHING', 'PRIVACY_VIOLATION', 'COPYRIGHT', 'TRADEMARK', 'MALWARE', 'ILLEGAL_CONTENT', 'SELF_HARM', 'PLATFORM_MANIPULATION', 'DECEPTIVE_PRACTICE', 'OTHER');

CREATE TYPE assessment_status_enum AS ENUM ('PENDING_REVIEW', 'CONFIRMED', 'NOT_CONFIRMED', 'INSUFFICIENT_EVIDENCE');

CREATE TABLE platforms (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	domain VARCHAR(255) NOT NULL, 
	reporting_url VARCHAR(500), 
	api_endpoint VARCHAR(500), 
	has_official_api BOOLEAN NOT NULL, 
	allowed_categories JSON NOT NULL, 
	required_fields JSON NOT NULL, 
	attachment_rules JSON NOT NULL, 
	rate_limit_notes TEXT, 
	terms_url VARCHAR(500), 
	privacy_requirements TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role role_enum NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	action VARCHAR(80) NOT NULL, 
	resource_type VARCHAR(50), 
	resource_id VARCHAR(80), 
	metadata_json JSON, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_logs_timestamp ON audit_logs (timestamp);

CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	event_type VARCHAR(80) NOT NULL, 
	message VARCHAR(500) NOT NULL, 
	resource_type VARCHAR(50), 
	resource_id VARCHAR(80), 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE api_credentials (
	id VARCHAR(36) NOT NULL, 
	platform_id VARCHAR(36) NOT NULL, 
	credential_type VARCHAR(50) NOT NULL, 
	encrypted_value TEXT NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id)
);

CREATE TABLE policies (
	id VARCHAR(36) NOT NULL, 
	platform_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	policy_url VARCHAR(500), 
	effective_date DATE, 
	last_updated DATE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id)
);

CREATE TABLE targets (
	id VARCHAR(36) NOT NULL, 
	platform_id VARCHAR(36) NOT NULL, 
	username VARCHAR(255) NOT NULL, 
	display_name VARCHAR(255), 
	profile_url VARCHAR(500) NOT NULL, 
	account_id VARCHAR(255), 
	profile_description TEXT, 
	account_created_at TIMESTAMP WITH TIME ZONE, 
	public_followers INTEGER, 
	public_following INTEGER, 
	public_posts INTEGER, 
	verification_status VARCHAR(30) NOT NULL, 
	collected_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	collected_by VARCHAR(36), 
	source_url VARCHAR(500) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id), 
	FOREIGN KEY(collected_by) REFERENCES users (id)
);

CREATE TABLE cases (
	id VARCHAR(36) NOT NULL, 
	case_number VARCHAR(30) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	platform_id VARCHAR(36) NOT NULL, 
	target_id VARCHAR(36), 
	report_category VARCHAR(50), 
	priority priority_enum NOT NULL, 
	description TEXT, 
	status case_status_enum NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id), 
	FOREIGN KEY(target_id) REFERENCES targets (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_cases_case_number ON cases (case_number);

CREATE TABLE policy_rules (
	id VARCHAR(36) NOT NULL, 
	policy_id VARCHAR(36) NOT NULL, 
	rule_code VARCHAR(50) NOT NULL, 
	category violation_category_enum NOT NULL, 
	description TEXT NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	keywords TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(policy_id) REFERENCES policies (id), 
	UNIQUE (rule_code)
);

CREATE TABLE contents (
	id VARCHAR(36) NOT NULL, 
	case_id VARCHAR(36) NOT NULL, 
	target_id VARCHAR(36) NOT NULL, 
	content_url VARCHAR(500) NOT NULL, 
	content_type VARCHAR(50), 
	excerpt TEXT, 
	observed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(target_id) REFERENCES targets (id)
);

CREATE TABLE violation_assessments (
	id VARCHAR(36) NOT NULL, 
	case_id VARCHAR(36) NOT NULL, 
	category assessment_category_enum NOT NULL, 
	policy_rule_id VARCHAR(36), 
	confidence FLOAT NOT NULL, 
	evidence_ids JSON NOT NULL, 
	reason TEXT, 
	missing_evidence JSON NOT NULL, 
	requires_human_review BOOLEAN NOT NULL, 
	status assessment_status_enum NOT NULL, 
	generated_by VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	reviewed_by VARCHAR(36), 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(policy_rule_id) REFERENCES policy_rules (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);

CREATE TABLE evidence (
	id VARCHAR(36) NOT NULL, 
	evidence_number VARCHAR(30) NOT NULL, 
	case_id VARCHAR(36) NOT NULL, 
	content_id VARCHAR(36), 
	type evidence_type_enum NOT NULL, 
	source_url VARCHAR(500) NOT NULL, 
	description TEXT, 
	stored_filename VARCHAR(255), 
	original_filename VARCHAR(255), 
	mime_type VARCHAR(120), 
	file_size BIGINT, 
	sha256 VARCHAR(64), 
	collected_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	collected_by VARCHAR(36) NOT NULL, 
	verification_status evidence_verification_status_enum NOT NULL, 
	verification_notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(content_id) REFERENCES contents (id), 
	FOREIGN KEY(collected_by) REFERENCES users (id)
);

CREATE INDEX ix_evidence_sha256 ON evidence (sha256);

CREATE UNIQUE INDEX ix_evidence_evidence_number ON evidence (evidence_number);

CREATE TABLE reports (
	id VARCHAR(36) NOT NULL, 
	report_number VARCHAR(30) NOT NULL, 
	case_id VARCHAR(36) NOT NULL, 
	assessment_id VARCHAR(36), 
	platform_id VARCHAR(36) NOT NULL, 
	body JSON NOT NULL, 
	report_hash VARCHAR(64) NOT NULL, 
	readiness_score FLOAT NOT NULL, 
	readiness_level readiness_level_enum NOT NULL, 
	missing_items JSON NOT NULL, 
	status report_status_enum NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(assessment_id) REFERENCES violation_assessments (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_reports_report_hash ON reports (report_hash);

CREATE UNIQUE INDEX ix_reports_report_number ON reports (report_number);

CREATE TABLE evidence_hashes (
	id VARCHAR(36) NOT NULL, 
	evidence_id VARCHAR(36) NOT NULL, 
	stage VARCHAR(20) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE chain_of_custody (
	id VARCHAR(36) NOT NULL, 
	evidence_id VARCHAR(36) NOT NULL, 
	action VARCHAR(50) NOT NULL, 
	performed_by VARCHAR(36) NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	previous_hash VARCHAR(64), 
	new_hash VARCHAR(64), 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id), 
	FOREIGN KEY(performed_by) REFERENCES users (id)
);

CREATE TABLE report_submissions (
	id VARCHAR(36) NOT NULL, 
	report_id VARCHAR(36) NOT NULL, 
	method VARCHAR(20) NOT NULL, 
	submitted_by VARCHAR(36) NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	external_reference VARCHAR(255), 
	platform_response JSON, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_id) REFERENCES reports (id), 
	FOREIGN KEY(submitted_by) REFERENCES users (id)
);

CREATE TABLE review_queue (
	id VARCHAR(36) NOT NULL, 
	case_id VARCHAR(36) NOT NULL, 
	assessment_id VARCHAR(36), 
	report_id VARCHAR(36), 
	status review_queue_status_enum NOT NULL, 
	assigned_to VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(assessment_id) REFERENCES violation_assessments (id), 
	FOREIGN KEY(report_id) REFERENCES reports (id), 
	FOREIGN KEY(assigned_to) REFERENCES users (id)
);

CREATE TABLE review_decisions (
	id VARCHAR(36) NOT NULL, 
	queue_item_id VARCHAR(36) NOT NULL, 
	reviewer_id VARCHAR(36) NOT NULL, 
	action review_action_enum NOT NULL, 
	notes TEXT, 
	decided_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(queue_item_id) REFERENCES review_queue (id), 
	FOREIGN KEY(reviewer_id) REFERENCES users (id)
);
