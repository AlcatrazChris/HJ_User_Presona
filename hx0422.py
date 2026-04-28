import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import Optional

st.set_page_config(page_title="华境S盲订用户画像", layout="wide")


# ══════════════════════════════════════════════════════════════
# ①  样式配置数据类  ——  所有样式参数的唯一来源
#    后期修改默认值 / 增删参数只需改这里
# ══════════════════════════════════════════════════════════════

@dataclass
class ChartStyle:
    # ── 颜色 ──────────────────────────────────────────────────
    bar_color:   str = "#67cbe4"
    font_color:  str = "#333333"

    # ── 字号 ──────────────────────────────────────────────────
    title_size:  int = 18
    axis_size:   int = 12
    label_size:  int = 11
    legend_size: int = 12

    # ── 元素开关 ──────────────────────────────────────────────
    show_x_ticks:    bool = False
    show_y_ticks:    bool = True
    show_grid:       bool = True
    show_axis_title: bool = False
    # "不显示" | "数量" | "百分比"
    label_mode:      str  = "数量"

    # ── 布局 ──────────────────────────────────────────────────
    legend_pos:   str   = "底部水平"   # "底部水平" | "顶部水平" | "右侧垂直"
    cols_per_row: int   = 2
    chart_height: int   = 480
    bar_width:    float = 0.6


# ══════════════════════════════════════════════════════════════
# ②  侧边栏面板渲染器  ——  UI 控件 ↔ ChartStyle 双向绑定
#    新增控件 → 在对应 expander 内添加即可，主程序无需改动
# ══════════════════════════════════════════════════════════════

_LEGEND_OPTIONS = ["底部水平", "顶部水平", "右侧垂直"]

def render_style_panel(style: ChartStyle) -> ChartStyle:
    """渲染集成样式面板，返回用户调整后的 ChartStyle。"""

    st.sidebar.markdown("---")

    # ── 标题行（带折叠图标感） ────────────────────────────────
    with st.sidebar.expander("样式设置", expanded=True):

        # —— 颜色 ————————————————————————————————————————————
        st.caption("颜色")
        c1, c2 = st.columns(2)
        style.bar_color  = c1.color_picker("主色", style.bar_color,  key="bc")
        style.font_color = c2.color_picker("字色", style.font_color, key="fc")

        st.markdown("<hr style='margin:6px 0'>", unsafe_allow_html=True)

        # —— 字号 ————————————————————————————————————————————
        st.caption("字号")
        col_a, col_b = st.columns(2)
        style.title_size  = col_a.number_input("标题", 10, 36, style.title_size,  key="ts")
        style.axis_size   = col_b.number_input("刻度", 8,  24, style.axis_size,   key="axs")
        style.legend_size = col_a.number_input("图例", 8,  24, style.legend_size, key="ls")
        style.label_size  = col_b.number_input("标签", 8,  20, style.label_size,  key="lbs")

        st.markdown("<hr style='margin:6px 0'>", unsafe_allow_html=True)

        # —— 元素开关（紧凑双列） ─────────────────────────────
        st.caption("显示元素")
        t1, t2 = st.columns(2)
        style.show_x_ticks    = t1.checkbox("X轴数值",  style.show_x_ticks,    key="sxt")
        style.show_y_ticks    = t2.checkbox("Y轴标签",  style.show_y_ticks,    key="syt")
        style.show_grid       = t1.checkbox("网格线",   style.show_grid,       key="sg")
        style.show_axis_title = t2.checkbox("轴标题",   style.show_axis_title, key="sat")

        _LABEL_OPTIONS = ["不显示", "数量", "百分比"]
        style.label_mode = st.radio(
            "数据标签", _LABEL_OPTIONS,
            index=_LABEL_OPTIONS.index(style.label_mode),
            horizontal=True, key="lm",
        )

        st.markdown("<hr style='margin:6px 0'>", unsafe_allow_html=True)

        # —— 布局 ————————————————————————————————————————————
        st.caption("布局")
        style.legend_pos   = st.radio("图例位置", _LEGEND_OPTIONS,
                                       index=_LEGEND_OPTIONS.index(style.legend_pos),
                                       horizontal=True, key="lp")
        style.cols_per_row = st.slider("每行图数",   1, 3,   style.cols_per_row, key="cpr")
        style.chart_height = st.slider("图表高度",   300, 900, style.chart_height, step=50, key="ch")
        style.bar_width    = st.slider("柱子宽度",   0.2, 1.0, style.bar_width,   step=0.05, key="bw")

    return style


# ══════════════════════════════════════════════════════════════
# ③  图表工厂  ——  生成 plotly Figure 并注入所有样式
# ══════════════════════════════════════════════════════════════

def _legend_layout(s: ChartStyle) -> dict:
    """计算图例位置参数"""
    tight = not s.show_x_ticks and not s.show_axis_title
    y_map = {
        "顶部水平": 1.02,
        "底部水平": -0.05 if tight else -0.25,
        "右侧垂直": 0.5,
    }
    return {
        "底部水平": dict(orientation="h", yanchor="top",    xanchor="center", x=0.5,  y=y_map["底部水平"]),
        "顶部水平": dict(orientation="h", yanchor="bottom", xanchor="center", x=0.5,  y=y_map["顶部水平"]),
        "右侧垂直": dict(orientation="v", yanchor="middle", xanchor="left",   x=1.02, y=0.5),
    }[s.legend_pos]


def _margin(s: ChartStyle) -> dict:
    """自适应计算边距"""
    tight = not s.show_x_ticks and not s.show_axis_title
    pos = s.legend_pos
    t = 100 + int(s.title_size * 0.5) if pos == "顶部水平" else 80 if pos == "右侧垂直" else 60
    b = 30  if (pos == "底部水平" and tight) else \
        100 if (pos == "底部水平") else 60
    r = 150 if pos == "右侧垂直" else 50
    return dict(t=t, b=b, l=50, r=r)


def apply_style(fig: go.Figure, title: str, s: ChartStyle) -> go.Figure:
    """将 ChartStyle 中的所有参数注入到 plotly Figure。"""
    fig.update_layout(
        title=dict(
            text=title, x=0.02,
            y=0.99 if s.legend_pos == "顶部水平" else 0.98,
            yanchor="top",
            font=dict(size=s.title_size, color=s.font_color),
        ),
        legend=dict(
            **_legend_layout(s),
            font=dict(size=s.legend_size, color=s.font_color),
        ),
        xaxis=dict(
            showgrid=s.show_grid, gridcolor="lightgrey",
            showticklabels=s.show_x_ticks,
            ticks="outside" if s.show_x_ticks else "",
            title=dict(text="数值" if s.show_axis_title else ""),
            tickfont=dict(size=s.axis_size, color=s.font_color),
            showline=True, linecolor="black",
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=s.show_y_ticks,
            tickfont=dict(size=s.axis_size, color=s.font_color),
            title=dict(text="" if not s.show_axis_title else None),
        ),
        margin=_margin(s),
        plot_bgcolor="white",
        height=s.chart_height,
    )
    fig.update_traces(
        width=s.bar_width,
        marker_line_color="white",
        marker_line_width=0.5,
        textfont_size=s.label_size,
    )
    return fig


# ══════════════════════════════════════════════════════════════
# ④  数据层  ——  加载 & 多选题处理（与业务逻辑完全解耦）
# ══════════════════════════════════════════════════════════════

@st.cache_data
def load_data():
    df = pd.read_excel("【用户画像】清洗后0422.xlsx")

    sort_orders = {
        "年龄段":     ["30岁以下","30-34岁","35-39岁","40-44岁","45-49岁","50岁以上"],
        "家庭结构":   ["单身","两口之家","三口之家","四口之家","五口之家","六口及以上"],
        "学历":       ["高中/中专及以下","大专","本科","硕士","博士"],
        "家庭年收入": ["15万以下","15-19万","20-24万","25-29万","30-39万","40-49万","50万以上"],
    }
    multi_cols = ["消费观念","通勤环境","触媒渠道","性能偏好","智能偏好","对比车型"]
    return df, sort_orders, multi_cols


def process_multi_choice(data: pd.DataFrame, col: str, top_n: Optional[int] = None) -> pd.DataFrame:
    """多选题统计：拆分 → 清洗 → 特殊处理 → TopN"""
    SKIP = {"nan","(跳过)","（跳过）","None","none"}

    expanded = data[col].astype(str).str.split("┋").explode().str.strip()
    expanded = expanded[~expanded.isin(SKIP)]

    # 字段专项处理
    if col in ("对比车型", "智能偏好"):
        expanded = expanded.apply(lambda x: "其他" if "其他" in x else x)

    counts = expanded.value_counts().reset_index()
    counts.columns = [col, "人数"]

    if col == "消费观念":
        counts[col] = counts[col].str[:4]
        counts = counts.groupby(col)["人数"].sum().reset_index().sort_values("人数", ascending=False)

    if col == "对比车型" and top_n:
        top_df      = counts.head(top_n)
        other_count = counts.iloc[top_n:]["人数"].sum()
        if other_count > 0:
            counts = (
                pd.concat([top_df, pd.DataFrame({col: ["其他"], "人数": [other_count]})], ignore_index=True)
                .groupby(col)["人数"].sum().reset_index()
                .sort_values("人数", ascending=False)
            )
        else:
            counts = top_df

    return counts


def get_counts(df: pd.DataFrame, metric: str, multi_cols: list) -> pd.DataFrame:
    """统一取单/多选题数据"""
    if metric in multi_cols:
        return process_multi_choice(df, metric)
    counts = df[metric][~df[metric].isin(["(跳过)", "nan"])].value_counts().reset_index()
    counts.columns = [metric, "人数"]
    return counts


def apply_sort(counts: pd.DataFrame, metric: str, sort_orders: dict) -> pd.DataFrame:
    """有预设顺序的按逻辑顺序排列，其他按人数降序。"""
    if metric in sort_orders:
        counts[metric] = pd.Categorical(counts[metric], categories=sort_orders[metric], ordered=True)
        counts = counts.sort_values(metric, ascending=False)
    else:
        counts = counts.sort_values("人数", ascending=True)   # px 水平条形图从下到上，ascending=True 使最大值在顶
    return counts


def label_format(sty: ChartStyle, total: Optional[int] = None) -> str | bool:
    """
    根据 label_mode 返回 plotly text_auto 参数或手动格式字符串。
    - "不显示" → False
    - "数量"   → True（plotly 自动整数）
    - "百分比" → 需外部先计算占比列，传 fmt 字符串
    """
    if sty.label_mode == "不显示":
        return False
    if sty.label_mode == "数量":
        return True          # plotly text_auto=True 显示原始数值
    # "百分比" — 由调用方决定格式串，这里返回标记
    return "pct"


# ══════════════════════════════════════════════════════════════
# ⑤  页面：整体画像总览
# ══════════════════════════════════════════════════════════════

def page_overview(df, sort_orders, multi_cols, sty: ChartStyle):
    st.title("项目用户画像全景图")
    METRICS = ["年龄段","家庭结构","学历","家庭年收入","职业","消费观念","通勤环境","触媒渠道","性能偏好","智能偏好","对比车型"]

    for i in range(0, len(METRICS), sty.cols_per_row):
        cols = st.columns(sty.cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(METRICS):
                break
            metric = METRICS[idx]
            with col:
                counts = apply_sort(get_counts(df, metric, multi_cols), metric, sort_orders)

                # 百分比模式：计算占比列作为文本，数量/不显示模式直接用 text_auto
                if sty.label_mode == "百分比":
                    total = counts["人数"].sum()
                    counts["标签"] = (counts["人数"] / total).map("{:.1%}".format) if total > 0 else ""
                    fig = px.bar(
                        counts, x="人数", y=metric, orientation="h",
                        text="标签",
                        color_discrete_sequence=[sty.bar_color],
                    )
                else:
                    fig = px.bar(
                        counts, x="人数", y=metric, orientation="h",
                        text_auto=(sty.label_mode == "数量"),
                        color_discrete_sequence=[sty.bar_color],
                    )

                st.plotly_chart(apply_style(fig, f"{metric}分布", sty), use_container_width=True)


# ══════════════════════════════════════════════════════════════
# ⑥  页面：大区维度对比
# ══════════════════════════════════════════════════════════════

def page_region_compare(df, sort_orders, multi_cols, sty: ChartStyle):
    st.title("各区域指标结构对比")

    COMPARE_METRICS = ["年龄段","家庭结构","学历","家庭年收入","职业","消费观念","通勤环境","触媒渠道","性能偏好","智能偏好","对比车型"]
    metric = st.selectbox("选择对比指标", COMPARE_METRICS)

    all_regions     = sorted(df["大区"].unique().tolist())
    REGION_ORDER    = ["华南","华东","中原","华北","中南","西南","西北","东北"]
    default_regions = [r for r in REGION_ORDER if r in all_regions]
    selected        = st.multiselect("选择对比大区", all_regions, default=default_regions)

    if not selected:
        return

    parts = []
    for region in selected:
        res = get_counts(df[df["大区"] == region], metric, multi_cols)
        if metric in sort_orders:
            res = pd.merge(
                pd.DataFrame({metric: sort_orders[metric]}),
                res, on=metric, how="left"
            ).fillna(0)
        total     = res["人数"].sum()
        res["占比"] = res["人数"] / total if total > 0 else 0
        res["大区"] = region
        parts.append(res)

    final    = pd.concat(parts)
    cat_ord  = {metric: sort_orders[metric]} if metric in sort_orders else {}

    # 大区对比图本身已是占比值，百分比/数量模式都基于占比列
    if sty.label_mode == "不显示":
        text_auto = False
    elif sty.label_mode == "百分比":
        text_auto = ".1%"
    else:  # 数量 — 对比图展示占比，退回百分比格式更合理
        text_auto = ".1%"

    fig = px.bar(
        final, x="大区", y="占比", color=metric,
        text_auto=text_auto,
        category_orders=cat_ord,
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    apply_style(fig, f"各区域 {metric} 结构对比", sty)
    fig.update_layout(barmode="stack", yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# 🚀  主入口
# ══════════════════════════════════════════════════════════════

def main():
    df, sort_orders, multi_cols = load_data()

    # 侧边栏：功能模式
    st.sidebar.header("控制面板")
    menu = st.sidebar.radio("功能模式", ["整体画像总览", "大区维度指标对比"])

    # 初始化样式配置（session 持久化）
    if "style" not in st.session_state:
        st.session_state.style = ChartStyle()

    # 渲染集成样式面板
    sty = render_style_panel(st.session_state.style)

    # 路由到对应页面
    if menu == "整体画像总览":
        page_overview(df, sort_orders, multi_cols, sty)
    else:
        page_region_compare(df, sort_orders, multi_cols, sty)


if __name__ == "__main__":
    main()