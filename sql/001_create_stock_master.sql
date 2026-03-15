create table stock_master (
    symbol varchar(12) primary key,
    name varchar(200) not null,
    market varchar(20) not null,
    instrument_type varchar(20) not null,
    is_active boolean not null default true,
    source varchar(30) not null default 'NAVER',
    created_at timestamp not null default now(),
    updated_at timestamp not null default now()
);
