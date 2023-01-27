
select @@version;
select * from sysobjects where name = 'logs' and xtype = 'U'
select * from sys.tables where xtype = 'U'

drop table wiretap_log;
if(not exists(select * from INFORMATION_SCHEMA.TABLES where TABLE_NAME = 'wiretap_log'))
begin
    create table wiretap_log(
        [id] int identity(1,1) primary key,
        [prevId] uniqueidentifier null,
        [nodeId] uniqueidentifier not null,
        [instance] nvarchar(200) not null,
        [timestamp] datetime2(3) not null,
        [scope] nvarchar(200) not null,
        [level] nvarchar(50) not null,
        [status] nvarchar(50) not null,
        [elapsed] float not null,
        [details] nvarchar(max) null,
        [attachment] nvarchar(max) null
    )
end;


truncate table wiretap_log;