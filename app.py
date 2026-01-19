import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

st.set_page_config(page_title="期权标杆数据追踪", layout="wide")

st.title("📈 交易指标自动化记录与分析")

# --- 1. 连接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 增强型数据解析函数 ---
def parse_raw_data(text):
    data_rows = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    for line in lines:
        # A. 处理 QQQ 头部 (兼容中英文冒号、逗号、空格)
        qqq_header = re.search(r"QQQ盘前现价[:：]?\s*([\d.]+)[,，]\s*昨收\s*([\d.]+)", line)
        if qqq_header:
            data_rows.append([current_date, "QQQ", "Pre-Market", float(qqq_header.group(1))])
            data_rows.append([current_date, "QQQ", "Last Close", float(qqq_header.group(2))])
            continue

        # B. 处理 NQ 头部 (兼容中英文冒号、逗号、空格)
        nq_header = re.search(r"NQ盘前现价[:：]?\s*([\d.]+)[,，]\s*昨收\s*([\d.]+)", line)
        if nq_header:
            data_rows.append([current_date, "NQ", "Pre-Market", float(nq_header.group(1))])
            data_rows.append([current_date, "NQ", "Last Close", float(nq_header.group(2))])
            continue

        # C. 处理 NQ 的三列数据格式 (例如: 25803  25973  Combo 4)
        # 匹配: 数字 + 空格 + 数字 + 空格 + 名称
        nq_val_match = re.findall(r"^(\d+\.?\d*)\s+(\d+\.?\d*)\s+(.+)$", line)
        if nq_val_match:
            p1, p2, label = nq_val_match[0]
            data_rows.append([current_date, "NQ", label.strip(), float(p2)]) # 取第二列 NQ 数值
            continue

        # D. 处理 QQQ 的两列数据格式 (例如: 627.04  Combo 4)
        # 匹配: 数字 + 空格 + 名称
        qqq_val_match = re.findall(r"^(\d+\.?\d*)\s+(.+)$", line)
        if qqq_val_match:
            price, label = qqq_val_match[0]
            # 排除掉已经是 NQ 的行
            data_rows.append([current_date, "QQQ", label.strip(), float(price)])
            continue

    df = pd.DataFrame(data_rows, columns=["Date", "Symbol", "Indicator", "Value"])
    return df

# --- 3. 界面侧边栏 ---
st.sidebar.header("数据录入")
raw_input = st.sidebar.text_area("请粘贴每日数据到此处:", height=400, placeholder="此处粘贴你的QQQ和NQ数据...")

if st.sidebar.button("解析并上传数据"):
    if raw_input:
        parsed_df = parse_raw_data(raw_input)
        
        if not parsed_df.empty:
            try:
                # 读取旧数据
                existing_data = conn.read(worksheet="Sheet1")
                
                # 合并并去重 (根据日期、标的、指标名称)
                updated_df = pd.concat([existing_data, parsed_df], ignore_index=True)
                updated_df = updated_df.drop_duplicates(subset=["Date", "Symbol", "Indicator"], keep='last')
                
                # 更新
                conn.update(worksheet="Sheet1", data=updated_df)
                st.sidebar.success(f"成功解析并上传 {len(parsed_df)} 条数据！")
                st.rerun() # 刷新界面显示新图表
            except Exception as e:
                st.sidebar.error(f"写入 Google Sheets 失败: {e}")
        else:
            st.sidebar.error("解析失败：未能从输入文本中识别出有效数据，请检查格式。")
    else:
        st.sidebar.warning("请输入数据")

# --- 4. 数据可视化 ---
try:
    df_main = conn.read(worksheet="Sheet1")
    
    if not df_main.empty:
        # 转换日期格式确保排序正确
        df_main['Date'] = pd.to_datetime(df_main['Date'])
        df_main = df_main.sort_values('Date')

        st.subheader("📊 历史轨迹可视化")
        
        tab1, tab2 = st.tabs(["QQQ 分析", "NQ 分析"])

        with tab1:
            qqq_all = df_main[df_main["Symbol"] == "QQQ"]
            if not qqq_all.empty:
                indicators = st.multiselect("选择 QQQ 指标", qqq_all["Indicator"].unique(), default=["Call Wall", "Put Wall", "Zero Gamma"])
                fig_qqq = px.line(qqq_all[qqq_all["Indicator"].isin(indicators)], x="Date", y="Value", color="Indicator", markers=True, template="plotly_dark")
                st.plotly_chart(fig_qqq, use_container_width=True)

        with tab2:
            nq_all = df_main[df_main["Symbol"] == "NQ"]
            if not nq_all.empty:
                indicators_nq = st.multiselect("选择 NQ 指标", nq_all["Indicator"].unique(), default=["Call Wall", "Put Wall", "Zero Gamma"])
                fig_nq = px.line(nq_all[nq_all["Indicator"].isin(indicators_nq)], x="Date", y="Value", color="Indicator", markers=True, template="plotly_dark")
                st.plotly_chart(fig_nq, use_container_width=True)

        with st.expander("查看原始数据表"):
            st.dataframe(df_main.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.info("尚未发现历史数据。")
except Exception as e:
    st.error(f"读取数据或绘图失败: {e}")
