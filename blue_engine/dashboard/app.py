import json, sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
from config import DATABASE_FILE
from storage.database import init_db, journal_stats

st.set_page_config(page_title='Blue Market AI Dashboard', layout='wide')
st.title('Blue Market AI Phase 5 Dashboard')
init_db()

if not Path(DATABASE_FILE).exists():
    st.warning('No database yet. Run python main.py and create signals first.')
    st.stop()
con = sqlite3.connect(DATABASE_FILE)
signals = pd.read_sql_query('SELECT * FROM signals ORDER BY id DESC', con)
journal = pd.read_sql_query('SELECT * FROM journal ORDER BY id DESC', con)
con.close()

c1,c2,c3,c4 = st.columns(4)
stats = journal_stats()
c1.metric('Closed trades', stats['closed_trades'])
c2.metric('Win rate', f"{stats['win_rate']}%")
c3.metric('Net PnL', stats['net_pnl'])
c4.metric('Profit factor', stats['profit_factor'])

tab1, tab2, tab3, tab4 = st.tabs(['Signals','Journal','Performance','Signal Details'])
with tab1:
    st.subheader('Latest Signals')
    st.dataframe(signals[['created_at','symbol','action','confidence','entry','stop_loss','target_1','target_2','lot_size']].head(100), use_container_width=True)
    if not signals.empty:
        st.plotly_chart(px.scatter(signals, x='created_at', y='confidence', color='symbol', hover_data=['action']), use_container_width=True)
with tab2:
    st.subheader('Auto Journal')
    st.dataframe(journal, use_container_width=True)
with tab3:
    if not journal.empty and 'pnl' in journal.columns:
        closed = journal[journal['result']!='OPEN'].copy()
        if not closed.empty:
            closed['cum_pnl'] = closed['pnl'].fillna(0).cumsum()
            st.plotly_chart(px.line(closed, x='closed_at', y='cum_pnl', title='Equity Curve / Cumulative PnL'), use_container_width=True)
            st.plotly_chart(px.histogram(closed, x='result', color='symbol', title='Results by Symbol'), use_container_width=True)
        else:
            st.info('Close trades from CLI to build performance stats.')
with tab4:
    st.subheader('Full Payload')
    if not signals.empty:
        idx = st.selectbox('Select signal id', signals['id'].tolist())
        payload = signals.loc[signals['id']==idx, 'payload'].iloc[0]
        try: st.json(json.loads(payload))
        except Exception: st.code(payload)
