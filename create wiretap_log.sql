
select @@version;
select * from sysobjects where name = 'logs' and xtype = 'U'
select * from sys.tables where xtype = 'U'

create schema dev;
drop table dev.wiretap_log;
if(not exists(select * from INFORMATION_SCHEMA.TABLES where TABLE_SCHEMA = 'dev' and TABLE_NAME = 'wiretap_log'))
begin
    create table dev.wiretap_log(
        [id] int identity(1,1) primary key,
        [instance] nvarchar(200) null,
        [parent_id] uniqueidentifier null,
        [unique_id] uniqueidentifier null,
        [timestamp] datetime2(3) not null,
        [activity] nvarchar(200) not null,
        [level] nvarchar(50) not null,
        [trace] nvarchar(50) null,
        [elapsed] decimal(10, 3) null,
        [message] nvarchar(1000) null,
        [details] nvarchar(max) null,
        [attachment] nvarchar(max) null
    )
end;


truncate table wiretap_log;

select convert(uniqueidentifier, '1c07e690d6d74972831fd45c1a761e7f');

