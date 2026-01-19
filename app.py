{\rtf1\ansi\ansicpg936\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import re\
from datetime import datetime\
from streamlit_gsheets import GSheetsConnection\
import plotly.express as px\
\
# \uc0\u35774 \u32622 \u39029 \u38754 \u37197 \u32622 \
st.set_page_config(page_title="\uc0\u26399 \u26435 \u26631 \u26438 \u25968 \u25454 \u36861 \u36394 ", layout="wide")\
\
st.title("\uc0\u55357 \u56520  \u20132 \u26131 \u25351 \u26631 \u33258 \u21160 \u21270 \u35760 \u24405 \u19982 \u20998 \u26512 ")\
\
# --- 1. \uc0\u36830 \u25509  Google Sheets ---\
# \uc0\u38656 \u35201 \u22312  .streamlit/secrets.toml \u20013 \u37197 \u32622  credentials\
conn = st.connection("gsheets", type=GSheetsConnection)\
\
# --- 2. \uc0\u25968 \u25454 \u35299 \u26512 \u20989 \u25968  ---\
def parse_raw_data(text):\
    data_rows = []\
    current_date = datetime.now().strftime("%Y-%m-%d")\
    \
    # \uc0\u25552 \u21462  QQQ \u29616 \u20215 \u21644 \u26152 \u25910 \
    qqq_header = re.search(r"QQQ\uc0\u30424 \u21069 \u29616 \u20215 \u65306 ([\\d.]+)\u65292 \u26152 \u25910 ([\\d.]+)", text)\
    if qqq_header:\
        data_rows.append([current_date, "QQQ", "Pre-Market", float(qqq_header.group(1))])\
        data_rows.append([current_date, "QQQ", "Last Close", float(qqq_header.group(2))])\
\
    # \uc0\u25552 \u21462  QQQ \u26631 \u26438 \u25968 \u25454 \
    qqq_levels = re.findall(r"(\\d+\\.?\\d*)\\t([a-zA-Z\\s\\d]+)(?=\\n|$)", text)\
    for price, label in qqq_levels:\
        data_rows.append([current_date, "QQQ", label.strip(), float(price)])\
\
    # \uc0\u25552 \u21462  NQ \u29616 \u20215 \u21644 \u26152 \u25910 \
    nq_header = re.search(r"NQ\uc0\u30424 \u21069 \u29616 \u20215 ([\\d.]+)\u65292 \u26152 \u25910 ([\\d.]+)", text)\
    if nq_header:\
        data_rows.append([current_date, "NQ", "Pre-Market", float(nq_header.group(1))])\
        data_rows.append([current_date, "NQ", "Last Close", float(nq_header.group(2))])\
\
    # \uc0\u25552 \u21462  NQ \u26631 \u26438 \u25968 \u25454  (\u38024 \u23545 \u20004 \u21015 \u25968 \u20540 \u30340 \u24773 \u20917 )\
    # \uc0\u21305 \u37197 \u27169 \u24335 \u65306 \u25968 \u23383  \u38190 \u30424 \u31354 \u26684 /\u21046 \u34920 \u31526  \u25968 \u23383  \u38190 \u30424 \u31354 \u26684 /\u21046 \u34920 \u31526  \u26631 \u31614 \
    nq_levels = re.findall(r"(\\d+\\.?\\d*)\\s+(\\d+\\.?\\d*)\\s+([a-zA-Z\\s\\d]+)(?=\\n|$)", text)\
    for p1, p2, label in nq_levels:\
        # \uc0\u36825 \u37324 \u23384 \u20648 \u31532 \u20108 \u21015  NQ \u30340 \u25968 \u20540 \u65292 \u22914 \u38656 \u31532 \u19968 \u21015 \u21487 \u20462 \u25913 \
        data_rows.append([current_date, "NQ", label.strip(), float(p2)])\
\
    df = pd.DataFrame(data_rows, columns=["Date", "Symbol", "Indicator", "Value"])\
    return df\
\
# --- 3. \uc0\u30028 \u38754 \u20391 \u36793 \u26639 \u65306 \u36755 \u20837 \u25968 \u25454  ---\
st.sidebar.header("\uc0\u25968 \u25454 \u24405 \u20837 ")\
raw_input = st.sidebar.text_area("\uc0\u35831 \u31896 \u36148 \u27599 \u26085 \u25968 \u25454 \u21040 \u27492 \u22788 :", height=400)\
if st.sidebar.button("\uc0\u35299 \u26512 \u24182 \u19978 \u20256 \u25968 \u25454 "):\
    if raw_input:\
        try:\
            # \uc0\u35299 \u26512 \u26032 \u25968 \u25454 \
            new_data = parse_raw_data(raw_input)\
            \
            # \uc0\u35835 \u21462 \u29616 \u26377 \u25968 \u25454 \
            existing_data = conn.read(worksheet="Sheet1")\
            \
            # \uc0\u21512 \u24182 \u25968 \u25454 \
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)\
            # \uc0\u21435 \u37325 \u65288 \u38450 \u27490 \u21516 \u19968 \u22825 \u37325 \u22797 \u19978 \u20256 \u65289 \
            updated_df = updated_df.drop_duplicates(subset=["Date", "Symbol", "Indicator"], keep='last')\
            \
            # \uc0\u26356 \u26032 \u21040  Google Sheets\
            conn.update(worksheet="Sheet1", data=updated_df)\
            st.sidebar.success("\uc0\u25968 \u25454 \u24050 \u25104 \u21151 \u20445 \u23384 \u33267  Google Sheets!")\
        except Exception as e:\
            st.sidebar.error(f"\uc0\u35299 \u26512 \u22833 \u36133 : \{e\}")\
    else:\
        st.sidebar.warning("\uc0\u35831 \u36755 \u20837 \u25968 \u25454 ")\
\
# --- 4. \uc0\u25968 \u25454 \u23637 \u31034 \u19982 \u20998 \u26512  ---\
try:\
    df_main = conn.read(worksheet="Sheet1")\
    \
    if not df_main.empty:\
        st.subheader("\uc0\u55357 \u56522  \u21382 \u21490 \u36712 \u36857 \u39044 \u35272 ")\
        \
        # \uc0\u31579 \u36873 \u22120 \
        col1, col2 = st.columns(2)\
        with col1:\
            symbol_choice = st.selectbox("\uc0\u36873 \u25321 \u26631 \u30340 ", df_main["Symbol"].unique())\
        with col2:\
            indicator_choices = st.multiselect(\
                "\uc0\u36873 \u25321 \u25351 \u26631 ", \
                df_main[df_main["Symbol"] == symbol_choice]["Indicator"].unique(),\
                default=["Call Wall", "Put Wall", "Zero Gamma"]\
            )\
\
        # \uc0\u32472 \u22270 \u25968 \u25454 \u20934 \u22791 \
        plot_df = df_main[(df_main["Symbol"] == symbol_choice) & (df_main["Indicator"].isin(indicator_choices))]\
        \
        if not plot_df.empty:\
            fig = px.line(\
                plot_df, \
                x="Date", \
                y="Value", \
                color="Indicator",\
                markers=True,\
                title=f"\{symbol_choice\} \uc0\u25351 \u26631 \u36208 \u21183 \u22270 ",\
                template="plotly_dark"\
            )\
            st.plotly_chart(fig, use_container_width=True)\
            \
            # \uc0\u25968 \u25454 \u34920 \u26684 \u23637 \u31034 \
            with st.expander("\uc0\u26597 \u30475 \u21407 \u22987 \u25968 \u25454 \u34920 "):\
                st.dataframe(df_main.sort_values(by="Date", ascending=False), use_container_width=True)\
        else:\
            st.info("\uc0\u35831 \u22312 \u19978 \u26041 \u36873 \u25321 \u25351 \u26631 \u20197 \u32472 \u22270 ")\
    else:\
        st.info("\uc0\u30446 \u21069  Google Sheets \u20013 \u27809 \u26377 \u25968 \u25454 \u65292 \u35831 \u20808 \u22312 \u20391 \u36793 \u26639 \u24405 \u20837 \u12290 ")\
\
except Exception as e:\
    st.error(f"\uc0\u35835 \u21462 \u25968 \u25454 \u22833 \u36133 : \{e\}")}