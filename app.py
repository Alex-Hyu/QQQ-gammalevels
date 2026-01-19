import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# 设置页面配置
st.set_page_config(page_title="期权标杆数据追踪", layout="wide")

st.title("📈 交易指标自动化记录与分析")

# --- 1. 连接 Google Sheets ---
# 需要在 .streamlit/secrets.toml 中配置 credentials
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 数据解析函数 ---
def parse_raw_data(text):
    data_rows = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 提取 QQQ 现价和昨收
    qqq_header = re.search(r"QQQ盘前现价：([\d.]+)，昨收([\d.]+)", text)
    if qqq_header:
        data_rows.append([current_date, "QQQ", "Pre-Market", float(qqq_header.group(1))])
        data_rows.append([current_date, "QQQ", "Last Close", float(qqq_header.group(2))])

    # 提取 QQQ 标杆数据
    qqq_levels = re.findall(r"(\d+\.?\d*)\t([a-zA-Z\s\d]+)(?=\n|$)", text)
    for price, label in qqq_levels:
        data_rows.append([current_date, "QQQ", label.strip(), float(price)])

    # 提取 NQ 现价和昨收
    nq_header = re.search(r"NQ盘前现价([\d.]+)，昨收([\d.]+)", text)
    if nq_header:
        data_rows.append([current_date, "NQ", "Pre-Market", float(nq_header.group(1))])
        data_rows.append([current_date, "NQ", "Last Close", float(nq_header.group(2))])

    # 提取 NQ 标杆数据 (针对两列数值的情况)
    # 匹配模式：数字 键盘空格/制表符 数字 键盘空格/制表符 标签
    nq_levels = re.findall(r"(\d+\.?\d*)\s+(\d+\.?\d*)\s+([a-zA-Z\s\d]+)(?=\n|$)", text)
    for p1, p2, label in nq_levels:
        # 这里存储第二列 NQ 的数值，如需第一列可修改
        data_rows.append([current_date, "NQ", label.strip(), float(p2)])

    df = pd.DataFrame(data_rows, columns=["Date", "Symbol", "Indicator", "Value"])
    return df

# --- 3. 界面侧边栏：输入数据 ---
st.sidebar.header("数据录入")
raw_input = st.sidebar.text_area("请粘贴每日数据到此处:", height=400)
if st.sidebar.button("解析并上传数据"):
    if raw_input:
        try:
            # 解析新数据
            new_data = parse_raw_data(raw_input)
            
            # 读取现有数据
            existing_data = conn.read(worksheet="Sheet1")
            
            # 合并数据
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            # 去重（防止同一天重复上传）
            updated_df = updated_df.drop_duplicates(subset=["Date", "Symbol", "Indicator"], keep='last')
            
            # 更新到 Google Sheets
            conn.update(worksheet="Sheet1", data=updated_df)
            st.sidebar.success("数据已成功保存至 Google Sheets!")
        except Exception as e:
            st.sidebar.error(f"解析失败: {e}")
    else:
        st.sidebar.warning("请输入数据")

# --- 4. 数据展示与分析 ---
try:
    df_main = conn.read(worksheet="Sheet1")
    
    if not df_main.empty:
        st.subheader("📊 历史轨迹预览")
        
        # 筛选器
        col1, col2 = st.columns(2)
        with col1:
            symbol_choice = st.selectbox("选择标的", df_main["Symbol"].unique())
        with col2:
            indicator_choices = st.multiselect(
                "选择指标", 
                df_main[df_main["Symbol"] == symbol_choice]["Indicator"].unique(),
                default=["Call Wall", "Put Wall", "Zero Gamma"]
            )

        # 绘图数据准备
        plot_df = df_main[(df_main["Symbol"] == symbol_choice) & (df_main["Indicator"].isin(indicator_choices))]
        
        if not plot_df.empty:
            fig = px.line(
                plot_df, 
                x="Date", 
                y="Value", 
                color="Indicator",
                markers=True,
                title=f"{symbol_choice} 指标走势图",
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 数据表格展示
            with st.expander("查看原始数据表"):
                st.dataframe(df_main.sort_values(by="Date", ascending=False), use_container_width=True)
        else:
            st.info("请在上方选择指标以绘图")
    else:
        st.info("目前 Google Sheets 中没有数据，请先在侧边栏录入。")

except Exception as e:
    st.error(f"读取数据失败: {e}")
