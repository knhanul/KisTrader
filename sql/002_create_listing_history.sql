create table instrument_listing_history (
    id bigserial primary key,
    symbol varchar(12) not null,
    name varchar(200) not null,
    market varchar(20) not null,
    instrument_type varchar(20) not null,
    is_active boolean not null default true,
    effective_date date not null,
    source varchar(30) not null default 'NAVER',
    created_at timestamp not null default now()
);
