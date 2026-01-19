import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

st.set_page_config(page_title="期权标杆数据追踪", layout="wide")

st.title("📈 交易指标自动化记录与分析")

# --- 1. 连接 Google Sheets ---
# 请确保你的表格标签页名称与下方 worksheet 变量一致
WORKSHEET_NAME = "Sheet1" # 如果你的表格底部叫“工作表1”，请改为“工作表1”

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 增强型数据解析函数 ---
def parse_raw_data(text):
    data_rows = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    for line in lines:
        qqq_header = re.search(r"QQQ盘前现价[:：]?\s*([\d.]+)[,，]\s*昨收\s*([\d.]+)", line)
        if qqq_header:
            data_rows.append([current_date, "QQQ", "Pre-Market", float(qqq_header.group(1))])
            data_rows.append([current_date, "QQQ", "Last Close", float(qqq_header.group(2))])
            continue

        nq_header = re.search(r"NQ盘前现价[:：]?\s*([\d.]+)[,，]\s*昨收\s*([\d.]+)", line)
        if nq_header:
            data_rows.append([current_date, "NQ", "Pre-Market", float(nq_header.group(1))])
            data_rows.append([current_date, "NQ", "Last Close", float(nq_header.group(2))])
            continue

        nq_val_match = re.findall(r"^(\d+\.?\d*)\s+(\d+\.?\d*)\s+(.+)$", line)
        if nq_val_match:
            p1, p2, label = nq_val_match[0]
            data_rows.append([current_date, "NQ", label.strip(), float(p2)])
            continue

        qqq_val_match = re.findall(r"^(\d+\.?\d*)\s+(.+)$", line)
        if qqq_val_match:
            price, label = qqq_val_match[0]
            data_rows.append([current_date, "QQQ", label.strip(), float(price)])
            continue

    return pd.DataFrame(data_rows, columns=["Date", "Symbol", "Indicator", "Value"])

# --- 3. 界面侧边栏 ---
st.sidebar.header("数据录入")
raw_input = st.sidebar.text_area("请粘贴每日数据到此处:", height=400)

if st.sidebar.button("解析并上传数据"):
    if raw_input:
        parsed_df = parse_raw_data(raw_input)
        if not parsed_df.empty:
            try:
                # 尝试读取现有数据
                try:
                    existing_data = conn.read(worksheet=WORKSHEET_NAME)
                except Exception:
                    # 如果读取失败（可能是空表），创建一个带表头的空 DataFrame
                    existing_data = pd.DataFrame(columns=["Date", "Symbol", "Indicator", "Value"])
                
                # 合并并清洗
                combined_df = pd.concat([existing_data, parsed_df], ignore_index=True)
                # 确保日期列是字符串方便去重
                combined_df['Date'] = combined_df['Date'].astype(str)
                combined_df = combined_df.drop_duplicates(subset=["Date", "Symbol", "Indicator"], keep='last')
                
                # 写回 Google Sheets
                conn.update(worksheet=WORKSHEET_NAME, data=combined_df)
                st.sidebar.success("✅ 数据已同步至 Google Sheets!")
                st.rerun()
            except Exception as e:
                # 这里会显示具体的错误原因
                st.sidebar.error(f"❌ Google Sheets 错误: {str(e)}")
                st.info("提示：请检查 1. API是否开启 2. 标签页名称是否叫 Sheet1 3. Secrets 里的私钥格式")
        else:
            st.sidebar.error("解析失败：未能识别数据，请检查输入格式。")

# --- 4. 数据展示与分析 ---
try:
    df_main = conn.read(worksheet=WORKSHEET_NAME)
    if df_main is not None and not df_main.empty:
        df_main['Date'] = pd.to_datetime(df_main['Date'])
        
        st.subheader("📊 历史轨迹可视化")
        tab1, tab2 = st.tabs(["QQQ 分析", "NQ 分析"])

        with tab1:
            qqq_all = df_main[df_main["Symbol"] == "QQQ"]
            if not qqq_all.empty:
                indicators = st.multiselect("选择 QQQ 指标", qqq_all["Indicator"].unique(), default=qqq_all["Indicator"].unique()[:3])
                fig_qqq = px.line(qqq_all[qqq_all["Indicator"].isin(indicators)], x="Date", y="Value", color="Indicator", markers=True, template="plotly_dark")
                st.plotly_chart(fig_qqq, use_container_width=True)

        with tab2:
            nq_all = df_main[df_main["Symbol"] == "NQ"]
            if not nq_all.empty:
                indicators_nq = st.multiselect("选择 NQ 指标", nq_all["Indicator"].unique(), default=nq_all["Indicator"].unique()[:3])
                fig_nq = px.line(nq_all[nq_all["Indicator"].isin(indicators_nq)], x="Date", y="Value", color="Indicator", markers=True, template="plotly_dark")
                st.plotly_chart(fig_nq, use_container_width=True)

        with st.expander("查看原始数据表"):
            st.dataframe(df_main.sort_values(by="Date", ascending=False), use_container_width=True)
except Exception:
    st.info("等待首次数据上传以生成图表...")
