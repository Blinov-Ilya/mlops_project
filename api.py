import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Request
from kafka import KafkaProducer
from kafka.errors import KafkaError
from psycopg.rows import dict_row
from pydantic import BaseModel, StringConstraints


class NewTicket(BaseModel):
    text: Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=1, max_length=1000, pattern=r'^[^\x00]+$',
    )]


class AcceptedTicket(BaseModel):
    ticket_id: UUID


class TicketResult(AcceptedTicket):
    text: str
    category: str
    created_at: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = KafkaProducer(
        bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
        value_serializer=lambda ticket: json.dumps(ticket).encode('utf-8'),
        acks='all',
        max_block_ms=5000,
    )
    app.state.producer = producer
    try:
        yield
    finally:
        producer.close()


app = FastAPI(title='Card Queue', lifespan=lifespan)


@app.post('/tickets', response_model=AcceptedTicket, status_code=202)
def submit_ticket(ticket: NewTicket, request: Request):
    ticket_id = str(uuid4())
    payload = {'ticket_id': ticket_id, 'text': ticket.text}
    try:
        request.app.state.producer.send('tickets', key=ticket_id.encode(), value=payload).get(timeout=5)
    except KafkaError as error:
        raise HTTPException(status_code=503, detail='Could not queue the ticket') from error
    return {'ticket_id': ticket_id}


@app.get('/tickets', response_model=list[TicketResult])
def recent_tickets():
    with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row) as connection:
        return connection.execute(
            '''
            SELECT ticket_id, text, category, created_at
            FROM ticket_results
            ORDER BY created_at DESC
            LIMIT 200
            '''
        ).fetchall()


@app.get('/tickets/{ticket_id}', response_model=TicketResult)
def get_ticket(ticket_id: UUID):
    with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row) as connection:
        ticket = connection.execute(
            '''
            SELECT ticket_id, text, category, created_at
            FROM ticket_results
            WHERE ticket_id = %s
            ''',
            (ticket_id,),
        ).fetchone()
    if ticket is None:
        raise HTTPException(status_code=404, detail='No saved prediction for this ticket')
    return ticket
