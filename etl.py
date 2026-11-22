import os

import psycopg
from dagster import DefaultScheduleStatus, Definitions, ScheduleDefinition, job, op


@op
def build_daily_counts():
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute('TRUNCATE daily_category_counts')
        connection.execute(
            '''
            INSERT INTO daily_category_counts (day, category, ticket_count)
            SELECT (created_at AT TIME ZONE 'UTC')::date AS day, category, count(*)
            FROM ticket_results
            GROUP BY day, category
            '''
        )


@job
def refresh_daily_counts():
    build_daily_counts()


defs = Definitions(
    jobs=[refresh_daily_counts],
    schedules=[ScheduleDefinition(
        job=refresh_daily_counts,
        cron_schedule='* * * * *',
        execution_timezone='UTC',
        default_status=DefaultScheduleStatus.RUNNING,
    )],
)
