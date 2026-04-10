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
    
    # 统一清理函数：处理百分号、空格并强制转为数字，无法转换的变为空值
    def clean_to_float(series):
        return pd.to_numeric(series.astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce')

    for col in ['修复胜率', '登场率']:
        if col in df_main.columns:
            df_main[col] = clean_to_float(df_main[col])
            
    if 'Ban率' in df_ban.columns:
        df_ban['Ban率'] = clean_to_float(df_ban['Ban率'])
    
    # 合并并删除缺失关键数据的行
    df_full = pd.merge(df_main, df_ban, on=['英雄名', 'MMR'], how='left')
    df_full = df_full.dropna(subset=['Ban率', '修复胜率', '登场率'])
    
    # 【修复处】确保此时 Ban率 已经是纯 float 格式再求均值
    overall_avg_ban = df_full['Ban率'].mean()
    
    df_full['Ban权值'] = df_full['Ban率'] * 10
    df_full['出现率'] = df_full['登场率'] + df_full['Ban权值']
    df_full['展示标签'] = df_full['英雄名'] + " (" + df_full['位置'] + ")"
    
    df_filtered = df_full[df_full['登场率'] > 0.75].copy()
    return df_filtered, overall_avg_ban

# --- 侧边栏 ---
st.sidebar.header("数据导入")
uploaded_file = st.sidebar.file_uploader("上传英雄数据 Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df, global_b_avg = process_data_logic(uploaded_file)
        
        st.write(f"### 🚨 平衡性概览")
        op_data, weak_data = [], []
        
        for (pos, name), group in df.groupby(['位置', '英雄名']):
            op_mmrs, weak_mmrs = [], []
            for _, row in group.iterrows():
                status = check_hero_status(row, global_b_avg)
                if status == 1: op_mmrs.append(row['MMR'])
                elif status == -1: weak_mmrs.append(row['MMR'])
            
            if op_mmrs:
                op_data.append({"超模英雄": f"[{pos}] {name}", "异常分段详情": ", ".join(op_mmrs), "异常计数": len(op_mmrs)})
            if len(weak_mmrs) >= 4:
                weak_data.append({"下水道(蛆)": f"[{pos}] {name}", "异常计数": len(weak_mmrs)})

        op_df = pd.DataFrame(op_data)
        if not op_df.empty:
            op_df = op_df.sort_values(by="异常计数", ascending=False).drop(columns=["异常计数"])
            op_df.index = range(1, len(op_df) + 1)

        weak_df = pd.DataFrame(weak_data)
        if not weak_df.empty:
            weak_df = weak_df.sort_values(by="异常计数", ascending=False).drop(columns=["异常计数"])
            weak_df.index = range(1, len(weak_df) + 1)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("🔥 **超模 (OP)**")
            if not op_df.empty: st.table(op_df)
            else: st.info("暂无超模英雄")
        with c2:
            st.markdown("💩 **蛆 (Underpowered)**")
            if not weak_df.empty: st.table(weak_df)
            else: st.info("暂无表现极差的英雄")

        st.markdown("---")
        
        positions = ['全部', '大龙路', '打野', '中路', '小龙路', '游走']
        mmrs = ['elite', 'high', 'normal', 'low']
        
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            selected_pos = st.radio("📍 选择位置视角:", positions, horizontal=True)
        with col_ctrl2:
            selected_mmr = st.radio("🏆 选择分段视角:", mmrs, horizontal=True)
        
        if selected_pos == '全部':
            filtered_df = df[df['MMR'] == selected_mmr].copy()
            label_col = '展示标签' 
        else:
            filtered_df = df[(df['位置'] == selected_pos) & (df['MMR'] == selected_mmr)].copy()
            label_col = '英雄名'   

        if not filtered_df.empty:
            if selected_mmr == 'elite':
                dynamic_height_bar = max(800, len(filtered_df) * 22) if selected_pos == '全部' else 800
                filtered_df = filtered_df.sort_values('出现率', ascending=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(y=filtered_df[label_col], x=filtered_df['Ban权值'], 
                                    name='Ban率*10', orientation='h', marker_color=COLOR_ABNORMAL))
                fig.add_trace(go.Bar(y=filtered_df[label_col], x=filtered_df['登场率'], 
                                    name='登场率', orientation='h', marker_color=COLOR_NORMAL))
                fig.add_vline(x=45, line_width=3, line_color=COLOR_BRIGHT_AXIS)
                fig.add_vline(x=5, line_width=3, line_color=COLOR_BRIGHT_AXIS)
                fig.update_layout(
                    barmode='stack', height=dynamic_height_bar, 
                    xaxis_title="出现率 (%) [左红:Ban压 | 右蓝:登场]",
                    xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickmode='linear', dtick=5),
                    showlegend=False, margin=dict(t=50, b=50, l=150, r=50)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                fixed_height_scatter = 1000
                y_ul, y_ur, y_lo = MMR_THRESHOLDS.get(selected_mmr, (54.5, 52.5, 49.0))
                filtered_df['平衡状态'] = filtered_df.apply(lambda r: "异常" if check_hero_status(r, global_b_avg) != 0 else "正常", axis=1)
                max_x = max(filtered_df['Ban率'].max(), 5 * global_b_avg) * 1.05
                min_y, max_y = min(filtered_df['修复胜率'].min(), y_lo) - 0.5, max(filtered_df['修复胜率'].max(), y_ul) + 0.5
                fig_2d = px.scatter(filtered_df, x='Ban率', y='修复胜率', size='登场率', text=label_col,
                                    color='平衡状态', color_discrete_map={'正常': COLOR_NORMAL, '异常': COLOR_ABNORMAL}, 
                                    height=fixed_height_scatter, size_max=40)
                fig_2d.update_traces(marker=dict(opacity=0.4, line=dict(width=1, color='rgba(50,50,50,0.1)')), 
                                     textposition='middle right', textfont=dict(size=10), cliponaxis=False)
                fig_2d.add_trace(go.Scatter(x=[0, global_b_avg, 5 * global_b_avg, max_x], y=[y_ul, y_ul, y_ur, y_ur],
                                            mode='lines', line=dict(color=COLOR_BRIGHT_AXIS, width=3), name='削弱线'))
                fig_2d.add_trace(go.Scatter(x=[0, max_x], y=[y_lo, y_lo], mode='lines', 
                                            line=dict(color=COLOR_BRIGHT_AXIS, width=3), name='加强线'))
                fig_2d.add_vline(x=0, line_width=2, line_color='rgba(80,80,80,0.6)')
                fig_2d.add_hline(y=40, line_width=2, line_color='rgba(80,80,80,0.6)')
                fig_2d.update_xaxes(ticksuffix='%', range=[-0.5, max_x], showgrid=True, gridcolor=GRID_COLOR)
                fig_2d.update_yaxes(ticksuffix='%', range=[min_y, max_y], showgrid=True, gridcolor=GRID_COLOR)
                fig_2d.update_layout(showlegend=False, margin=dict(t=50, b=50, l=50, r=50))
                st.plotly_chart(fig_2d, use_container_width=True)
            
    except Exception as e:
        st.error(f"处理错误: {e}")
else:
    st.info("👈 请在左侧上传 Excel 文件。")
