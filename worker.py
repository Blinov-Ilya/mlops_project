import json
import os
from pathlib import Path

import joblib
import psycopg
from kafka import KafkaConsumer, TopicPartition
from kafka.structs import OffsetAndMetadata


def main():
    model = joblib.load(Path(__file__).with_name('model.joblib'))
    database = os.environ['DATABASE_URL']
    consumer = KafkaConsumer(
        'tickets',
        bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
        group_id='card-queue-worker',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=json.loads,
    )

    try:
        for message in consumer:
            ticket = message.value
            category = str(model.predict([ticket['text']])[0])
            with psycopg.connect(database) as connection:
                connection.execute(
                    '''
                    INSERT INTO ticket_results (ticket_id, text, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticket_id) DO NOTHING
                    ''',
                    (ticket['ticket_id'], ticket['text'], category),
                )

            # Смещение сохраняется после фиксации транзакции в базе.
            partition = TopicPartition(message.topic, message.partition)
            consumer.commit({partition: OffsetAndMetadata(message.offset + 1, '', -1)})
            print(f'{ticket["ticket_id"]}: {category}')
    finally:
        consumer.close()


if __name__ == '__main__':
    main()
