import streamlit as st
import pandas as pd
import plotly.express as px

# 设置页面配置
st.set_page_config(page_title="用户画像分析系统", layout="wide")


# --- 1. 数据加载与预处理 ---
@st.cache_data
def load_data():
    # 读取数据
    df = pd.read_excel("【用户画像】清洗后0422.xlsx")

    # 逻辑排序顺序（涵盖所有边界字段）
    sort_orders = {
        "年龄段": ["30岁以下", "30-34岁", "35-39岁", "40-44岁", "45-49岁", "50岁以上"],
        "家庭结构": ["单身", "两口之家", "三口之家", "四口之家", "五口之家", "六口及以上" ],
        "学历": ["高中/中专及以下", "大专", "本科", "硕士", "博士"],
        "家庭年收入": ["15万以下", "15-19万", "20-24万", "25-29万", "30-39万", "40-49万", "50万以上"]
    }

    # 多选题字段
    multi_choice_cols = ["消费观念", "通勤环境", "触媒渠道", "性能偏好", "智能偏好", "对比车型"]

    return df, sort_orders, multi_choice_cols


df, sort_orders, multi_choice_cols = load_data()


# --- 2. 核心处理函数 ---
def process_multi_choice(data, column, top_n=None):
    """处理多选题统计，包含清洗逻辑、过滤逻辑和截断逻辑"""
    # 拆分数据
    expanded = data[column].astype(str).str.split('┋').explode().str.strip()

    # 基础过滤：剔除无效项和（跳过）项
    skip_tags = ['nan', '(跳过)', '（跳过）', 'None', 'none']
    expanded = expanded[~expanded.isin(skip_tags)]

    # 优化点1：对比车型中，包含“其他（小鹏...）”这类长文本的全部统一为“其他”
    if column == "对比车型":
        expanded = expanded.apply(lambda x: "其他" if "其他" in str(x) else x)

    # 优化点2：智能偏好中，排除“其他”项
    if column == "智能偏好":
        expanded = expanded.apply(lambda x: "其他" if "其他" in str(x) else x)

    # 统计人数
    counts = expanded.value_counts().reset_index()
    counts.columns = [column, '人数']

    # 优化点3：消费观念仅展示前4个字（在统计后进行名称映射，保证统计准确）
    if column == "消费观念":
        counts[column] = counts[column].astype(str).str[:4]
        # 截断后可能会产生重复项（如前4字相同），需重新合并统计
        counts = counts.groupby(column)['人数'].sum().reset_index().sort_values('人数', ascending=False)

    # 对对比车型进行 TopN 处理
    if column == "对比车型" and top_n:
        top_df = counts.head(top_n)
        other_count = counts.iloc[top_n:]['人数'].sum()
        if other_count > 0:
            other_df = pd.DataFrame({column: ['其他'], '人数': [other_count]})
            # 再次去重合并（防止原本就有“其他”，合并后变两个其他）
            counts = pd.concat([top_df, other_df], ignore_index=True).groupby(column)['人数'].sum().reset_index()
            counts = counts.sort_values('人数', ascending=False)
        else:
            counts = top_df

    return counts


# --- 3. 侧边栏导航 ---
st.sidebar.title("控制面板")
mode = st.sidebar.radio("选择模式", ["总览", "对比"])

# --- 4. 总览模式 ---
if mode == "总览":
    st.title("用户画像总览")

    regions = ["全国"] + sorted(df["大区"].unique().tolist())
    selected_region = st.selectbox("选择区域", regions)

    plot_df = df if selected_region == "全国" else df[df["大区"] == selected_region]
    st.markdown(f"<p style='color:gray; font-size:14px;'>当前有效问卷份数：{len(plot_df)} 份</p>",
                unsafe_allow_html=True)

    metrics = ["年龄段", "家庭结构", "学历", "家庭年收入", "职业", "消费观念",
               "是否增换购", "通勤环境", "触媒渠道", "性能偏好", "智能偏好", "对比车型"]

    cols = st.columns(3)
    for i, metric in enumerate(metrics):
        with cols[i % 3]:
            if metric in multi_choice_cols:
                res = process_multi_choice(plot_df, metric, top_n=10 if metric == "对比车型" else None)
                res = res.sort_values("人数", ascending=True)
            else:
                # 过滤单选题跳过项
                filtered_series = plot_df[metric][~plot_df[metric].astype(str).isin(['(跳过)', '（跳过）'])]
                res = filtered_series.value_counts().reset_index()
                res.columns = [metric, '人数']

                if metric in sort_orders:
                    res[metric] = pd.Categorical(res[metric], categories=sort_orders[metric], ordered=True)
                    res = res.sort_values(metric, ascending=False).dropna(subset=[metric])
                else:
                    res = res.sort_values("人数", ascending=True)

            fig = px.bar(res, x='人数', y=metric, orientation='h',
                         title=f"{metric} 分布", text='人数',
                         color_discrete_sequence=['#81bcde'])

            fig.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=20),
                              xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)

# --- 5. 对比模式 ---
else:
    st.title("大区维度指标对比")

    compare_metric = st.selectbox("选择对比指标", ["年龄段", "家庭结构", "学历", "家庭年收入", "职业",
                                                   "消费观念", "是否增换购", "通勤环境", "触媒渠道",
                                                   "性能偏好", "智能偏好", "对比车型"])

    all_regions = sorted(df["大区"].unique().tolist())
    selected_regions = st.multiselect("选择参与对比的大区", all_regions, default=all_regions[:2])

    if not selected_regions:
        st.warning("请至少选择一个大区进行对比")
    else:
        comparison_data = []
        for region in selected_regions:
            reg_df = df[df["大区"] == region]

            if compare_metric in multi_choice_cols:
                res = process_multi_choice(reg_df, compare_metric, top_n=10 if compare_metric == "对比车型" else None)
            else:
                filtered_series = reg_df[compare_metric][~reg_df[compare_metric].astype(str).isin(['(跳过)', '（跳过）'])]
                res = filtered_series.value_counts().reset_index()
                res.columns = [compare_metric, '人数']

            if not res.empty:
                res['大区'] = region
                res['占比'] = res['人数'] / res['人数'].sum()
                comparison_data.append(res)

        if comparison_data:
            final_compare_df = pd.concat(comparison_data)

            cat_orders_dict = {}
            if compare_metric in sort_orders:
                cat_orders_dict[compare_metric] = sort_orders[compare_metric]

            fig = px.bar(final_compare_df,
                         x="大区",
                         y="占比",
                         color=compare_metric,
                         title=f"各区域 {compare_metric} 结构对比",
                         orientation='v',
                         text_auto='.1%',
                         category_orders=cat_orders_dict)

            if len(selected_regions) == 1:
                fig.update_traces(width=0.2)
            elif len(selected_regions) == 2:
                fig.update_traces(width=0.4)

            fig.update_layout(yaxis_tickformat='.0%',
                              xaxis_title="大区",
                              yaxis_title="占比 (%)",
                              legend_title=compare_metric,
                              barmode='stack',
                              height=650)

            st.plotly_chart(fig, use_container_width=True)