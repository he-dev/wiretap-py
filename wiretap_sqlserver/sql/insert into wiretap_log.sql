
INSERT INTO dev.wiretap_log(
    [parent_id],
    [unique_id],
    [timestamp],
    [activity],
    [trace],
    [level],
    [elapsed],
    [message],
    [details],
    [attachment]
) VALUES (
    :parent_id,
    :unique_id,
    :timestamp,
    :activity,
    :trace,
    :level,
    :elapsed,
    :message,
    :details,
    :attachment
)