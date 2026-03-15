create table investor_intraday_trade (
    id bigserial primary key,
    trade_date date not null,
    symbol varchar(12) not null,
    market varchar(20),
    time_slot varchar(10) not null,
    investor_type varchar(30) not null,
    net_buy_amount bigint,
    net_buy_volume bigint,
    buy_amount bigint,
    sell_amount bigint,
    buy_volume bigint,
    sell_volume bigint,
    source varchar(30) not null default 'KIS',
    created_at timestamp not null default now(),
    updated_at timestamp not null default now(),
    unique (trade_date, symbol, time_slot, investor_type)
);
