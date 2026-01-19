import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

st.set_page_config(page_title="期权标杆数据追踪", layout="wide")

st.title("📈 交易指标自动化记录与分析")

# --- 1. 连接 Google Sheets ---
WORKSHEET_NAME = "Sheet1" 
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 解析函数 (保持不变) ---
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

# --- 3. 侧边栏录入 ---
st.sidebar.header("数据录入")
raw_input = st.sidebar.text_area("请粘贴每日数据:", height=300)
if st.sidebar.button("解析并上传"):
    if raw_input:
        new_df = parse_raw_data(raw_input)
        if not new_df.empty:
            try:
                try:
                    old_df = conn.read(worksheet=WORKSHEET_NAME)
                except:
                    old_df = pd.DataFrame(columns=["Date", "Symbol", "Indicator", "Value"])
                
                final_df = pd.concat([old_df, new_df], ignore_index=True)
                final_df['Date'] = final_df['Date'].astype(str)
                final_df = final_df.drop_duplicates(subset=["Date", "Symbol", "Indicator"], keep='last')
                conn.update(worksheet=WORKSHEET_NAME, data=final_df)
                st.sidebar.success("同步成功！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"上传错误: {e}")

# --- 4. 数据可视化与调试 ---
try:
    # 强制清除缓存读取最新数据
    df_main = conn.read(worksheet=WORKSHEET_NAME, ttl=0)
    
    if df_main is not None and not df_main.empty:
        # --- 调试代码：如果你看不到图，请看这部分输出 ---
        with st.expander("🛠 数据源调试 (如果图表不显示，请检查列名)"):
            st.write("表格列名:", df_main.columns.tolist())
            st.write("数据预览:", df_main.head())
        
        # 统一处理日期
        df_main['Date'] = pd.to_datetime(df_main['Date']).dt.date
        df_main = df_main.sort_values('Date')

        st.subheader("📊 指标走势分析")
        
        # 获取所有唯一的指标
        all_symbols = df_main["Symbol"].unique()
        
        for sym in all_symbols:
            st.markdown(f"### {sym} 数据序列")
            sub_df = df_main[df_main["Symbol"] == sym]
            
            # 自动选择前几个指标作为默认显示
            available_indicators = sub_df["Indicator"].unique().tolist()
            selected = st.multiselect(f"选择 {sym} 的指标:", available_indicators, default=available_indicators[:3], key=f"select_{sym}")
            
            plot_data = sub_df[sub_df["Indicator"].isin(selected)]
            
            if not plot_data.empty:
                # 即使只有一天数据，也强制显示点(markers=True)
                fig = px.line(
                    plot_data, 
                    x="Date", 
                    y="Value", 
                    color="Indicator", 
                    markers=True, 
                    title=f"{sym} 走势图",
                    template="plotly_dark"
                )
                # 解决只有一天数据时 X 轴显示不佳的问题
                fig.update_xaxes(type='category') 
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"请在上方选择想查看的 {sym} 指标")

    else:
        st.info("💡 还没发现数据，请先在左侧粘贴并点击上传。")

except Exception as e:
    st.error(f"读取异常: {e}")
