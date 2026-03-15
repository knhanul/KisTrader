create table batch_job_log (
    id bigserial primary key,
    job_name varchar(50) not null,
    run_type varchar(20) not null,
    started_at timestamp not null,
    finished_at timestamp,
    status varchar(20) not null,
    message text,
    total_count integer,
    success_count integer,
    fail_count integer,
    created_at timestamp not null default now()
);
