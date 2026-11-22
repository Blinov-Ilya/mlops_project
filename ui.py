import os
import time

import pandas as pd
import requests
import streamlit as st


API_URL = os.environ['API_URL']
QUEUES = {
    'card_arrival': 'Card delivery',
    'lost_or_stolen_card': 'Lost or stolen card',
    'card_swallowed': 'Card retained by ATM',
    'declined_card_payment': 'Declined card payment',
    'card_payment_not_recognised': 'Unrecognized card payment',
}


def wait_for_result(ticket_id):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = requests.get(f'{API_URL}/tickets/{ticket_id}', timeout=3)
        if response.status_code != 404:
            response.raise_for_status()
            return response.json()
        time.sleep(0.5)
    return None


def submit_ticket(text):
    try:
        response = requests.post(f'{API_URL}/tickets', json={'text': text}, timeout=12)
        response.raise_for_status()
        ticket_id = response.json()['ticket_id']
    except requests.RequestException:
        st.error('Could not submit the ticket. Try again in a moment.')
        return

    try:
        with st.spinner('Processing'):
            result = wait_for_result(ticket_id)
    except requests.RequestException:
        st.error(f'Could not fetch the prediction. Ticket ID: {ticket_id}')
        return

    if result is None:
        st.info(f'The ticket is still in the queue. Refresh history in a moment. Ticket ID: {ticket_id}')
        return

    st.success(f'Suggested queue: {QUEUES[result["category"]]}')


def show_history():
    st.header('Recent tickets')
    st.caption('Latest 200 completed tickets. Dates are in UTC.')
    st.button('Refresh history')

    try:
        response = requests.get(f'{API_URL}/tickets', timeout=3)
        response.raise_for_status()
    except requests.RequestException:
        st.error('Could not load ticket history.')
        return

    history = pd.DataFrame(response.json())
    if history.empty:
        st.info('Completed tickets will appear here.')
        return

    history['created_at'] = pd.to_datetime(history['created_at'], format='ISO8601', utc=True)
    history['Day'] = history['created_at'].dt.floor('D').dt.tz_localize(None)
    dates, queues = st.columns(2)
    period = dates.date_input('Date range (UTC)', value=(history['Day'].min(), history['Day'].max()))
    selected = queues.multiselect('Queues', list(QUEUES), format_func=QUEUES.get)

    if len(period) == 2:
        history = history[history['Day'].dt.date.between(*period)]
    if selected:
        history = history[history['category'].isin(selected)]
    if history.empty:
        st.info('No tickets match these filters.')
        return

    history = history.assign(Queue=history['category'].map(QUEUES)).rename(columns={
        'created_at': 'Received (UTC)', 'text': 'Ticket', 'ticket_id': 'Ticket ID',
    })
    st.dataframe(history[['Received (UTC)', 'Ticket', 'Queue', 'Ticket ID']], hide_index=True)

    by_queue, by_day = st.columns(2)
    by_queue.subheader('Tickets by queue')
    by_queue.bar_chart(history.groupby('Queue').size().rename('Tickets'))
    by_day.subheader('Tickets per day')
    by_day.bar_chart(history.groupby('Day').size().rename('Tickets'))


st.set_page_config(page_title='Card Queue', layout='wide')
st.title('Card Queue')
st.link_button('Swagger API', os.environ['SWAGGER_URL'])

with st.form('new_ticket'):
    text = st.text_area('Bank support ticket', placeholder='The ATM kept my card', max_chars=1000)
    sent = st.form_submit_button('Suggest a queue')

if sent:
    if text.strip():
        submit_ticket(text)
    else:
        st.warning('Enter the ticket text.')

show_history()
