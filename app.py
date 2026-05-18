import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 页面配置
st.set_page_config(page_title="英雄数据专业平衡性分析系统", layout="wide")

# --- 视觉配色方案 ---
COLOR_NORMAL = '#7D99C8'    # 柔和灰蓝
COLOR_ABNORMAL = '#E67E7E'  # 柔和珊瑚红
COLOR_BRIGHT_AXIS = '#FFB300' # 明亮的警戒线
GRID_COLOR = 'rgba(200, 200, 200, 0.3)'

# ==========================================
# ⚙️ 平衡性参数配置表
# ==========================================
MMR_THRESHOLDS = {
    'low':    (54.5, 52.5, 49.0),
    'normal': (54.5, 52.5, 49.0),
    'high':   (54.0, 52.0, 49.0)
}

def check_hero_status(row, global_b_avg):
    mmr = row['MMR']
    if mmr == 'elite':
        presence = row['出现率']
        if presence > 45: return 1   
        if presence < 5: return -1   
        return 0
    
    br = row['Ban率']
    wr = row['修复胜率']
    y_upper_left, y_upper_right, y_lower = MMR_THRESHOLDS.get(mmr, (54.5, 52.5, 49.0))
    
    if br <= global_b_avg:
        upper_limit = y_upper_left
    elif br >= 5 * global_b_avg:
        upper_limit = y_upper_right
    else:
        slope = (y_upper_right - y_upper_left) / (4 * global_b_avg)
        upper_limit = y_upper_left + slope * (br - global_b_avg)
    
    if wr > upper_limit: return 1
    if wr < y_lower: return -1
    return 0

def process_data_logic(file):
    cols_to_keep = ['英雄名', '位置', 'MMR', '修复胜率', '登场率']
    df_main = pd.read_excel(file, sheet_name='SheetData', usecols=cols_to_keep)
    df_ban = pd.read_excel(file, sheet_name='SheetData1')
    
    def clean_to_float(series):
        return pd.to_numeric(series.astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce')

    for col in ['修复胜率', '登场率']:
        if col in df_main.columns:
            df_main[col] = clean_to_float(df_main[col])
