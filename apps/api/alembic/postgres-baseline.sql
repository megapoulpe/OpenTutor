-- Frozen application schema at revision 20261028_0026. Fresh databases only.

CREATE TABLE users (
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(255), 
	hashed_password VARCHAR(255), 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE cognitive_baselines (
	user_id UUID NOT NULL, 
	avg_message_length FLOAT NOT NULL, 
	avg_word_count FLOAT NOT NULL, 
	help_seeking_rate FLOAT NOT NULL, 
	message_count INTEGER NOT NULL, 
	session_count INTEGER NOT NULL, 
	total_length FLOAT NOT NULL, 
	total_words FLOAT NOT NULL, 
	help_count INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (user_id)
);

CREATE TABLE courses (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	metadata JSONB, 
	active_scene VARCHAR(50), 
	template_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE learning_templates (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	is_builtin BOOLEAN NOT NULL, 
	created_by UUID, 
	preferences JSONB NOT NULL, 
	scene_id VARCHAR(50), 
	tab_preset JSONB, 
	workflow VARCHAR(50), 
	target_audience VARCHAR(100), 
	tags JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE auth_sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	domain VARCHAR(200) NOT NULL, 
	session_name VARCHAR(100) NOT NULL, 
	auth_type VARCHAR(30) NOT NULL, 
	is_valid BOOLEAN NOT NULL, 
	last_validated_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	login_actions JSONB, 
	login_url TEXT, 
	check_url TEXT, 
	success_selector VARCHAR(200), 
	failure_selector VARCHAR(200), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (session_name)
);

CREATE INDEX ix_auth_sessions_domain ON auth_sessions (domain);

CREATE TABLE integration_credentials (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	integration_name VARCHAR(50) NOT NULL, 
	access_token TEXT NOT NULL, 
	refresh_token TEXT, 
	token_expires_at TIMESTAMP WITH TIME ZONE, 
	scopes JSONB, 
	extra_data JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_integration UNIQUE (user_id, integration_name), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE course_content_tree (
	id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	parent_id UUID, 
	title VARCHAR(500) NOT NULL, 
	content TEXT, 
	level INTEGER NOT NULL, 
	order_index INTEGER NOT NULL, 
	source_file VARCHAR(500), 
	source_type VARCHAR(20) NOT NULL, 
	content_category VARCHAR(50), 
	blocks_json JSONB, 
	search_vector TEXT, 
	embedding TEXT, 
	metadata JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(parent_id) REFERENCES course_content_tree (id) ON DELETE CASCADE
);

CREATE INDEX ix_content_tree_course_order ON course_content_tree (course_id, order_index);

CREATE INDEX ix_content_tree_course_parent ON course_content_tree (course_id, parent_id);

CREATE INDEX ix_content_tree_search_vector ON course_content_tree (search_vector);

CREATE TABLE user_preferences (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	scope VARCHAR(20) NOT NULL, 
	scene_type VARCHAR(50), 
	dimension VARCHAR(50) NOT NULL, 
	value TEXT NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	confidence FLOAT NOT NULL, 
	dismissed_at TIMESTAMP WITH TIME ZONE, 
	dismissal_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_user_preference_user ON user_preferences (user_id);

CREATE TABLE preference_signals (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	signal_type VARCHAR(20) NOT NULL, 
	dimension VARCHAR(50) NOT NULL, 
	value TEXT NOT NULL, 
	context JSONB, 
	dismissed_at TIMESTAMP WITH TIME ZONE, 
	dismissal_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE TABLE conversation_memories (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	summary TEXT NOT NULL, 
	memory_type VARCHAR(20) NOT NULL, 
	category VARCHAR(100), 
	embedding TEXT, 
	search_vector TEXT, 
	importance FLOAT NOT NULL, 
	access_count INTEGER NOT NULL, 
	source_message TEXT, 
	metadata_json JSONB, 
	dismissed_at TIMESTAMP WITH TIME ZONE, 
	dismissal_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL
);

CREATE INDEX ix_mem_user_course ON conversation_memories (user_id, course_id);

CREATE INDEX ix_mem_search_vector ON conversation_memories (search_vector);

CREATE INDEX ix_mem_user_type ON conversation_memories (user_id, memory_type);

CREATE INDEX ix_mem_user_course_created ON conversation_memories (user_id, course_id, created_at);

CREATE TABLE ingestion_jobs (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	source_type VARCHAR(20) NOT NULL, 
	original_filename VARCHAR(500), 
	url TEXT, 
	mime_type VARCHAR(100), 
	file_path VARCHAR(1000), 
	file_size INTEGER, 
	content_hash VARCHAR(64), 
	course_id UUID, 
	course_preset BOOLEAN NOT NULL, 
	content_category VARCHAR(50), 
	classification_method VARCHAR(20), 
	status VARCHAR(20) NOT NULL, 
	progress_percent INTEGER NOT NULL, 
	phase_label VARCHAR(100), 
	embedding_status VARCHAR(20) NOT NULL, 
	nodes_created INTEGER NOT NULL, 
	error_message TEXT, 
	dispatched BOOLEAN NOT NULL, 
	dispatched_to JSONB, 
	user_corrected_category VARCHAR(50), 
	user_corrected_course UUID, 
	extracted_markdown TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_ingestion_jobs_content_hash ON ingestion_jobs (content_hash);

CREATE TABLE study_sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	duration_minutes INTEGER, 
	messages_sent INTEGER NOT NULL, 
	problems_attempted INTEGER NOT NULL, 
	problems_correct INTEGER NOT NULL, 
	notes_viewed INTEGER NOT NULL, 
	signals_extracted INTEGER NOT NULL, 
	metadata_json JSONB, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE TABLE chat_sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	scene_id VARCHAR(50), 
	title TEXT, 
	channel VARCHAR(30), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_chat_session_user_course_updated ON chat_sessions (user_id, course_id, updated_at);

CREATE INDEX ix_chat_session_user_course ON chat_sessions (user_id, course_id);

CREATE TABLE generated_assets (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	asset_type VARCHAR(50) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content JSONB NOT NULL, 
	metadata JSONB, 
	batch_id UUID NOT NULL, 
	version INTEGER NOT NULL, 
	is_archived BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL
);

CREATE TABLE study_plans (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	scene_id VARCHAR(50), 
	tasks JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE TABLE study_goals (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	title VARCHAR(200) NOT NULL, 
	objective TEXT NOT NULL, 
	success_metric VARCHAR(200), 
	current_milestone VARCHAR(200), 
	next_action VARCHAR(200), 
	status VARCHAR(20) NOT NULL, 
	confidence VARCHAR(20), 
	target_date TIMESTAMP WITH TIME ZONE, 
	metadata_json JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_study_goal_user_course_status_created ON study_goals (user_id, course_id, status, created_at);

CREATE INDEX ix_study_goal_user_status_target ON study_goals (user_id, status, target_date);

CREATE TABLE agent_kv (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	namespace VARCHAR(64) NOT NULL, 
	key VARCHAR(256) NOT NULL, 
	value_json JSONB NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_agent_kv_user_course_ns_key UNIQUE (user_id, course_id, namespace, key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_agent_kv_user_ns ON agent_kv (user_id, namespace);

CREATE TABLE mastery_snapshots (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	content_node_id UUID, 
	mastery_score FLOAT NOT NULL, 
	gap_type VARCHAR(30), 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_mastery_snap_user_course_time ON mastery_snapshots (user_id, course_id, recorded_at);

CREATE TABLE notifications (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	title VARCHAR(200) NOT NULL, 
	body TEXT NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	read BOOLEAN NOT NULL, 
	batch_key VARCHAR(200), 
	dedup_key VARCHAR(200), 
	priority VARCHAR(20), 
	scheduled_for TIMESTAMP WITH TIME ZONE, 
	sent_via JSONB, 
	action_url VARCHAR(500), 
	action_label VARCHAR(100), 
	metadata_json JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE TABLE usage_events (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	agent_name VARCHAR(64), 
	scene VARCHAR(64), 
	model_provider VARCHAR(64) NOT NULL, 
	model_name VARCHAR(128) NOT NULL, 
	input_tokens INTEGER NOT NULL, 
	output_tokens INTEGER NOT NULL, 
	estimated_cost_usd FLOAT NOT NULL, 
	tool_calls INTEGER NOT NULL, 
	metadata_json JSONB, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL
);

CREATE INDEX ix_usage_events_user_id ON usage_events (user_id);

CREATE INDEX ix_usage_events_created_at ON usage_events (created_at);

CREATE TABLE intervention_outcomes (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	intervention_type VARCHAR(50) NOT NULL, 
	block_type VARCHAR(50) NOT NULL, 
	signal_source VARCHAR(50) NOT NULL, 
	reason TEXT, 
	cognitive_load_before FLOAT, 
	cognitive_load_after FLOAT, 
	was_effective BOOLEAN, 
	user_feedback VARCHAR(20), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_intervention_user_course_time ON intervention_outcomes (user_id, course_id, created_at);

CREATE INDEX ix_intervention_unresolved ON intervention_outcomes (user_id, resolved_at);

CREATE TABLE practice_problems (
	id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	content_node_id UUID, 
	question_type VARCHAR(20) NOT NULL, 
	question TEXT NOT NULL, 
	options JSONB, 
	correct_answer TEXT, 
	explanation TEXT, 
	order_index INTEGER NOT NULL, 
	knowledge_points JSONB, 
	source VARCHAR(20), 
	difficulty_layer INTEGER, 
	problem_metadata JSONB, 
	parent_problem_id UUID, 
	is_diagnostic BOOLEAN NOT NULL, 
	source_batch_id UUID, 
	source_version INTEGER NOT NULL, 
	is_archived BOOLEAN NOT NULL, 
	source_owner VARCHAR(20) NOT NULL, 
	locked BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(content_node_id) REFERENCES course_content_tree (id) ON DELETE SET NULL, 
	FOREIGN KEY(parent_problem_id) REFERENCES practice_problems (id) ON DELETE SET NULL
);

CREATE INDEX ix_practice_problem_course ON practice_problems (course_id);

CREATE TABLE assignments (
	id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	due_date TIMESTAMP WITH TIME ZONE, 
	assignment_type VARCHAR(50), 
	source_ingestion_id UUID, 
	status VARCHAR(20) NOT NULL, 
	metadata_json JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(source_ingestion_id) REFERENCES ingestion_jobs (id) ON DELETE SET NULL
);

CREATE TABLE learning_progress (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	content_node_id UUID, 
	status VARCHAR(20) NOT NULL, 
	mastery_score FLOAT NOT NULL, 
	time_spent_minutes INTEGER NOT NULL, 
	review_count INTEGER NOT NULL, 
	quiz_attempts INTEGER NOT NULL, 
	quiz_correct INTEGER NOT NULL, 
	gap_type VARCHAR(30), 
	next_review_at TIMESTAMP WITH TIME ZONE, 
	ease_factor FLOAT NOT NULL, 
	interval_days INTEGER NOT NULL, 
	fsrs_difficulty FLOAT NOT NULL, 
	fsrs_stability FLOAT NOT NULL, 
	fsrs_reps INTEGER NOT NULL, 
	fsrs_lapses INTEGER NOT NULL, 
	fsrs_state VARCHAR(20) NOT NULL, 
	last_studied_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(content_node_id) REFERENCES course_content_tree (id) ON DELETE CASCADE
);

CREATE TABLE scrape_sources (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	url TEXT NOT NULL, 
	label VARCHAR(300), 
	source_type VARCHAR(30) NOT NULL, 
	requires_auth BOOLEAN NOT NULL, 
	auth_domain VARCHAR(200), 
	session_name VARCHAR(100), 
	enabled BOOLEAN NOT NULL, 
	interval_hours INTEGER NOT NULL, 
	last_scraped_at TIMESTAMP WITH TIME ZONE, 
	last_content_hash VARCHAR(64), 
	last_status VARCHAR(20), 
	last_error TEXT, 
	consecutive_failures INTEGER NOT NULL, 
	last_ingestion_id UUID, 
	metadata_json JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_scrape_sources_source_type CHECK (source_type IN ('generic', 'canvas')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(last_ingestion_id) REFERENCES ingestion_jobs (id) ON DELETE SET NULL
);

CREATE TABLE chat_message_logs (
	id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	metadata_json JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_chat_message_session_created ON chat_message_logs (session_id, created_at);

CREATE TABLE agent_tasks (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	goal_id UUID, 
	task_type VARCHAR(50) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	summary TEXT, 
	source VARCHAR(30) NOT NULL, 
	input_json JSONB, 
	metadata_json JSONB, 
	result_json JSONB, 
	error_message TEXT, 
	attempts INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	requires_approval BOOLEAN NOT NULL, 
	task_kind VARCHAR(30) NOT NULL, 
	risk_level VARCHAR(20) NOT NULL, 
	approval_status VARCHAR(20) NOT NULL, 
	approval_reason TEXT, 
	approval_action TEXT, 
	checkpoint_json JSONB, 
	step_results_json JSONB, 
	provenance_json JSONB, 
	approved_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	cancel_requested_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(goal_id) REFERENCES study_goals (id) ON DELETE SET NULL
);

CREATE INDEX ix_agent_task_user_status_created ON agent_tasks (user_id, status, created_at);

CREATE INDEX ix_agent_task_user_course_created ON agent_tasks (user_id, course_id, created_at);

CREATE INDEX ix_agent_task_status_approval_created ON agent_tasks (status, requires_approval, created_at);

CREATE TABLE knowledge_nodes (
	id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description VARCHAR(500), 
	content_node_id UUID, 
	metadata JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_knowledge_node_course_name UNIQUE (course_id, name), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(content_node_id) REFERENCES course_content_tree (id) ON DELETE SET NULL
);

CREATE TABLE practice_results (
	id UUID NOT NULL, 
	problem_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	user_answer TEXT NOT NULL, 
	is_correct BOOLEAN NOT NULL, 
	ai_explanation TEXT, 
	error_category VARCHAR(30), 
	difficulty_layer INTEGER, 
	answer_time_ms INTEGER, 
	answered_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(problem_id) REFERENCES practice_problems (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_practice_result_user_problem ON practice_results (user_id, problem_id);

CREATE TABLE wrong_answers (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	problem_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	user_answer TEXT NOT NULL, 
	correct_answer TEXT, 
	explanation TEXT, 
	error_category VARCHAR(30), 
	knowledge_points JSONB, 
	diagnosis VARCHAR(30), 
	error_detail JSONB, 
	review_count INTEGER NOT NULL, 
	last_reviewed_at TIMESTAMP WITH TIME ZONE, 
	mastered BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(problem_id) REFERENCES practice_problems (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX ix_wrong_answers_user_course ON wrong_answers (user_id, course_id);

CREATE INDEX ix_wrong_answers_course_mastered ON wrong_answers (course_id, mastered);

CREATE TABLE agenda_runs (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	course_id UUID, 
	goal_id UUID, 
	trigger VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	top_signal_type VARCHAR(50), 
	signals_json JSONB, 
	decision_json JSONB, 
	task_id UUID, 
	dedup_key VARCHAR(300), 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(goal_id) REFERENCES study_goals (id) ON DELETE SET NULL, 
	FOREIGN KEY(task_id) REFERENCES agent_tasks (id) ON DELETE SET NULL
);

CREATE INDEX ix_agenda_run_user_course_created ON agenda_runs (user_id, course_id, created_at);

CREATE INDEX ix_agenda_run_user_created ON agenda_runs (user_id, created_at);

CREATE INDEX ix_agenda_run_dedup ON agenda_runs (user_id, dedup_key, created_at);

CREATE TABLE knowledge_edges (
	id UUID NOT NULL, 
	source_id UUID NOT NULL, 
	target_id UUID NOT NULL, 
	relation_type VARCHAR(30) NOT NULL, 
	weight FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_knowledge_edge UNIQUE (source_id, target_id, relation_type), 
	FOREIGN KEY(source_id) REFERENCES knowledge_nodes (id) ON DELETE CASCADE, 
	FOREIGN KEY(target_id) REFERENCES knowledge_nodes (id) ON DELETE CASCADE
);

CREATE TABLE concept_mastery (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	knowledge_node_id UUID NOT NULL, 
	mastery_score FLOAT NOT NULL, 
	practice_count INTEGER NOT NULL, 
	correct_count INTEGER NOT NULL, 
	wrong_count INTEGER NOT NULL, 
	last_practiced_at TIMESTAMP WITH TIME ZONE, 
	next_review_at TIMESTAMP WITH TIME ZONE, 
	stability_days FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_concept_mastery_user_node UNIQUE (user_id, knowledge_node_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(knowledge_node_id) REFERENCES knowledge_nodes (id) ON DELETE CASCADE
);
