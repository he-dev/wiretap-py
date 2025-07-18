INSERT = """
INSERT INTO dev.wiretap_log(
    [instance],
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
    :instance, 
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
"""

