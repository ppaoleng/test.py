import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="Pile Reaction Calculator",
    page_icon="🏗️",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
    .main {
        background-color: #f7f9fc;
    }
    .title-box {
        background: linear-gradient(90deg, #1f4e79, #2e75b6);
        padding: 22px;
        border-radius: 16px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    .title-box h1 {
        margin: 0;
        font-size: 32px;
    }
    .title-box p {
        margin-top: 8px;
        font-size: 16px;
    }
    .metric-card {
        background-color: white;
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 6px solid #2e75b6;
        margin-bottom: 12px;
    }
    .metric-card h3 {
        margin: 0;
        font-size: 15px;
        color: #555;
    }
    .metric-card p {
        margin: 6px 0 0 0;
        font-size: 26px;
        font-weight: 700;
        color: #1f4e79;
    }
    .pass-box {
        background-color: #e8f5e9;
        color: #1b5e20;
        padding: 14px;
        border-radius: 12px;
        border-left: 6px solid #2e7d32;
        font-weight: 700;
    }
    .fail-box {
        background-color: #ffebee;
        color: #b71c1c;
        padding: 14px;
        border-radius: 12px;
        border-left: 6px solid #c62828;
        font-weight: 700;
    }
    .warn-box {
        background-color: #fff8e1;
        color: #e65100;
        padding: 14px;
        border-radius: 12px;
        border-left: 6px solid #ff9800;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# FUNCTIONS
# =========================================================
def calculate_centroid(df: pd.DataFrame):
    """
    Calculate centroid of pile group.
    If all piles are assumed identical, centroid is simple average.
    """
    x_bar = df["x_cm"].mean()
    y_bar = df["y_cm"].mean()
    return x_bar, y_bar


def calculate_reactions(df: pd.DataFrame, P_ton: float, ex_cm: float, ey_cm: float):
    """
    Calculate pile reactions under eccentric vertical load.

    Coordinate convention:
    - x positive to the right
    - y positive upward
    - ex = eccentricity in x direction from pile-group centroid
    - ey = eccentricity in y direction from pile-group centroid

    Moment:
    Mx = P * ey
    My = P * ex

    Reaction:
    Ri = P/n + (Mx * yi / sum(yi^2)) + (My * xi / sum(xi^2))

    Where xi and yi are pile coordinates measured from pile-group centroid.
    """
    df = df.copy()

    x_bar, y_bar = calculate_centroid(df)

    df["x_rel_cm"] = df["x_cm"] - x_bar
    df["y_rel_cm"] = df["y_cm"] - y_bar

    n = len(df)
    P_each = P_ton / n

    Mx_ton_cm = P_ton * ey_cm
    My_ton_cm = P_ton * ex_cm

    sum_x2 = np.sum(df["x_rel_cm"] ** 2)
    sum_y2 = np.sum(df["y_rel_cm"] ** 2)

    # Avoid division by zero
    if sum_x2 == 0:
        df["reaction_from_My_ton"] = 0.0
    else:
        df["reaction_from_My_ton"] = My_ton_cm * df["x_rel_cm"] / sum_x2

    if sum_y2 == 0:
        df["reaction_from_Mx_ton"] = 0.0
    else:
        df["reaction_from_Mx_ton"] = Mx_ton_cm * df["y_rel_cm"] / sum_y2

    df["reaction_basic_ton"] = P_each
    df["reaction_total_ton"] = (
        df["reaction_basic_ton"]
        + df["reaction_from_Mx_ton"]
        + df["reaction_from_My_ton"]
    )

    summary = {
        "x_bar": x_bar,
        "y_bar": y_bar,
        "P_total": P_ton,
        "P_each": P_each,
        "Mx": Mx_ton_cm,
        "My": My_ton_cm,
        "sum_x2": sum_x2,
        "sum_y2": sum_y2,
        "R_max": df["reaction_total_ton"].max(),
        "R_min": df["reaction_total_ton"].min(),
        "R_sum": df["reaction_total_ton"].sum()
    }

    return df, summary


def create_plan_plot(
    df_result: pd.DataFrame,
    cap_width_cm: float,
    cap_length_cm: float,
    x_bar: float,
    y_bar: float,
    ex_cm: float,
    ey_cm: float,
    safe_capacity_ton: float
):
    """
    Create simple graphic plan view.
    """
    load_x = x_bar + ex_cm
    load_y = y_bar + ey_cm

    x_min = -cap_length_cm / 2
    x_max = cap_length_cm / 2
    y_min = -cap_width_cm / 2
    y_max = cap_width_cm / 2

    fig = go.Figure()

    # Pile cap rectangle
    fig.add_shape(
        type="rect",
        x0=x_min,
        y0=y_min,
        x1=x_max,
        y1=y_max,
        line=dict(color="black", width=3),
        fillcolor="lightgray",
        opacity=0.45
    )

    # Center lines
    fig.add_shape(
        type="line",
        x0=x_min,
        y0=0,
        x1=x_max,
        y1=0,
        line=dict(color="red", width=1.5, dash="dash")
    )
    fig.add_shape(
        type="line",
        x0=0,
        y0=y_min,
        x1=0,
        y1=y_max,
        line=dict(color="red", width=1.5, dash="dash")
    )

    # Piles
    colors = []
    for r in df_result["reaction_total_ton"]:
        if r < 0:
            colors.append("#d32f2f")
        elif r > safe_capacity_ton:
            colors.append("#f57c00")
        else:
            colors.append("#2e7d32")

    fig.add_trace(
        go.Scatter(
            x=df_result["x_cm"],
            y=df_result["y_cm"],
            mode="markers+text",
            marker=dict(
                size=42,
                color=colors,
                line=dict(color="black", width=2),
                symbol="circle"
            ),
            text=[
                f"{row['Pile']}<br>R={row['reaction_total_ton']:.2f} ton"
                for _, row in df_result.iterrows()
            ],
            textposition="top center",
            name="Pile Reaction"
        )
    )

    # Centroid
    fig.add_trace(
        go.Scatter(
            x=[x_bar],
            y=[y_bar],
            mode="markers+text",
            marker=dict(size=16, color="blue", symbol="x"),
            text=["CG"],
            textposition="bottom center",
            name="Pile Group Centroid"
        )
    )

    # Load point
    fig.add_trace(
        go.Scatter(
            x=[load_x],
            y=[load_y],
            mode="markers+text",
            marker=dict(size=18, color="red", symbol="star"),
            text=[f"Load Point<br>ex={ex_cm:.1f} cm, ey={ey_cm:.1f} cm"],
            textposition="top center",
            name="Load Point"
        )
    )

    # Eccentricity arrow
    fig.add_annotation(
        x=load_x,
        y=load_y,
        ax=x_bar,
        ay=y_bar,
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=1.2,
        arrowwidth=2,
        arrowcolor="red"
    )

    fig.update_layout(
        title="Graphic Plan View: Pile Cap, Piles, Centroid and Eccentric Load",
        xaxis_title="x coordinate (cm)",
        yaxis_title="y coordinate (cm)",
        height=650,
        plot_bgcolor="white",
        showlegend=True,
        xaxis=dict(scaleanchor="y", scaleratio=1),
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig


def export_to_excel(df_result: pd.DataFrame, summary: dict, safe_capacity_ton: float):
    """
    Export calculation result to Excel.
    """
    output = BytesIO()

    summary_df = pd.DataFrame({
        "Item": [
            "Total vertical load P",
            "Basic reaction per pile",
            "Mx = P × ey",
            "My = P × ex",
            "Σx²",
            "Σy²",
            "Maximum reaction",
            "Minimum reaction",
            "Sum of reactions",
            "Allowable pile capacity"
        ],
        "Value": [
            summary["P_total"],
            summary["P_each"],
            summary["Mx"],
            summary["My"],
            summary["sum_x2"],
            summary["sum_y2"],
            summary["R_max"],
            summary["R_min"],
            summary["R_sum"],
            safe_capacity_ton
        ],
        "Unit": [
            "ton",
            "ton/pile",
            "ton-cm",
            "ton-cm",
            "cm²",
            "cm²",
            "ton",
            "ton",
            "ton",
            "ton/pile"
        ]
    })

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        df_result.to_excel(writer, sheet_name="Pile Reactions", index=False)

    return output.getvalue()


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="title-box">
        <h1>🏗️ Pile Reaction Calculator for Eccentric Load</h1>
        <p>โปรแกรมคำนวณแรงปฏิกิริยาเสาเข็มจากแรงแนวดิ่งเยื้องศูนย์ รองรับเสาเข็ม 2–4 ต้น</p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# SIDEBAR INPUT
# =========================================================
st.sidebar.header("1) ข้อมูลฐานราก / Pile Cap")

cap_length_cm = st.sidebar.number_input(
    "ความยาวฐานราก L ตามแกน x (cm)",
    min_value=10.0,
    value=190.0,
    step=10.0
)

cap_width_cm = st.sidebar.number_input(
    "ความกว้างฐานราก B ตามแกน y (cm)",
    min_value=10.0,
    value=190.0,
    step=10.0
)

st.sidebar.header("2) ข้อมูลน้ำหนักและกำลังรับน้ำหนัก")

P_ton = st.sidebar.number_input(
    "น้ำหนักกระทำต่อฐานราก P (ton)",
    min_value=0.01,
    value=150.0,
    step=10.0
)

safe_capacity_ton = st.sidebar.number_input(
    "กำลังรับน้ำหนักปลอดภัยของเสาเข็ม (ton/pile)",
    min_value=0.01,
    value=40.0,
    step=5.0
)

st.sidebar.header("3) การเยื้องศูนย์ของแรงกระทำ")

ex_cm = st.sidebar.number_input(
    "ex: ระยะเยื้องศูนย์ตามแกน x (cm)",
    value=0.0,
    step=1.0,
    help="ค่าบวก = เยื้องไปทางขวา"
)

ey_cm = st.sidebar.number_input(
    "ey: ระยะเยื้องศูนย์ตามแกน y (cm)",
    value=0.0,
    step=1.0,
    help="ค่าบวก = เยื้องขึ้นด้านบน"
)

st.sidebar.header("4) ข้อมูลเสาเข็ม")

n_piles = st.sidebar.selectbox(
    "จำนวนเสาเข็ม",
    options=[2, 3, 4],
    index=2
)

st.sidebar.caption("พิกัด x, y ให้อ้างอิงจากจุดศูนย์กลางฐานราก")

# Default layout for 4 piles based on a square-like arrangement
default_positions = {
    2: [(-60.0, 0.0), (60.0, 0.0)],
    3: [(-60.0, -60.0), (60.0, -60.0), (0.0, 60.0)],
    4: [(-60.0, 60.0), (60.0, 60.0), (-60.0, -60.0), (60.0, -60.0)]
}

pile_data = []

for i in range(n_piles):
    default_x, default_y = default_positions[n_piles][i]

    with st.sidebar.expander(f"เสาเข็ม Pile {i+1}", expanded=True):
        pile_name = st.text_input(
            f"ชื่อเสาเข็ม {i+1}",
            value=f"P{i+1}",
            key=f"pile_name_{i}"
        )

        x_cm = st.number_input(
            f"x{i+1} (cm)",
            value=default_x,
            step=1.0,
            key=f"x_{i}"
        )

        y_cm = st.number_input(
            f"y{i+1} (cm)",
            value=default_y,
            step=1.0,
            key=f"y_{i}"
        )

        pile_data.append({
            "Pile": pile_name,
            "x_cm": x_cm,
            "y_cm": y_cm
        })

df_piles = pd.DataFrame(pile_data)

# =========================================================
# CALCULATION
# =========================================================
df_result, summary = calculate_reactions(df_piles, P_ton, ex_cm, ey_cm)

df_result["status"] = np.where(
    df_result["reaction_total_ton"] < 0,
    "Uplift / แรงดึง",
    np.where(
        df_result["reaction_total_ton"] > safe_capacity_ton,
        "เกินกำลังรับน้ำหนัก",
        "ผ่าน"
    )
)

# Check pile inside cap
df_result["inside_cap"] = (
    (df_result["x_cm"] >= -cap_length_cm / 2)
    & (df_result["x_cm"] <= cap_length_cm / 2)
    & (df_result["y_cm"] >= -cap_width_cm / 2)
    & (df_result["y_cm"] <= cap_width_cm / 2)
)

all_inside = df_result["inside_cap"].all()
all_safe = (
    (df_result["reaction_total_ton"] <= safe_capacity_ton).all()
    and (df_result["reaction_total_ton"] >= 0).all()
    and all_inside
)

# =========================================================
# DISPLAY METRICS
# =========================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Total Load</h3>
            <p>{P_ton:.2f} ton</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Max Reaction</h3>
            <p>{summary["R_max"]:.2f} ton</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Min Reaction</h3>
            <p>{summary["R_min"]:.2f} ton</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Allowable</h3>
            <p>{safe_capacity_ton:.2f} ton</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# STATUS
# =========================================================
if all_safe:
    st.markdown(
        """
        <div class="pass-box">
            ✅ ผลการตรวจสอบ: ผ่าน — แรงปฏิกิริยาเสาเข็มทุกต้นไม่เกินกำลังรับน้ำหนักปลอดภัย และไม่มี uplift
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    if not all_inside:
        st.markdown(
            """
            <div class="fail-box">
                ❌ ผลการตรวจสอบ: ไม่ผ่าน — มีเสาเข็มอยู่นอกขอบเขตฐานราก
            </div>
            """,
            unsafe_allow_html=True
        )
    elif (df_result["reaction_total_ton"] < 0).any():
        st.markdown(
            """
            <div class="fail-box">
                ❌ ผลการตรวจสอบ: ไม่ผ่าน — มีเสาเข็มเกิดแรงดึงหรือ uplift
            </div>
            """,
            unsafe_allow_html=True
        )
    elif (df_result["reaction_total_ton"] > safe_capacity_ton).any():
        st.markdown(
            """
            <div class="fail-box">
                ❌ ผลการตรวจสอบ: ไม่ผ่าน — มีเสาเข็มรับแรงมากกว่ากำลังรับน้ำหนักปลอดภัย
            </div>
            """,
            unsafe_allow_html=True
        )

# =========================================================
# MAIN CONTENT
# =========================================================
left, right = st.columns([1.15, 0.85])

with left:
    st.subheader("📌 Graphic แสดงตำแหน่งเสาเข็มและแรงเยื้องศูนย์")

    fig = create_plan_plot(
        df_result=df_result,
        cap_width_cm=cap_width_cm,
        cap_length_cm=cap_length_cm,
        x_bar=summary["x_bar"],
        y_bar=summary["y_bar"],
        ex_cm=ex_cm,
        ey_cm=ey_cm,
        safe_capacity_ton=safe_capacity_ton
    )

    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("📊 ตารางผลการคำนวณ")

    display_df = df_result.copy()
    display_df = display_df[
        [
            "Pile",
            "x_cm",
            "y_cm",
            "x_rel_cm",
            "y_rel_cm",
            "reaction_basic_ton",
            "reaction_from_Mx_ton",
            "reaction_from_My_ton",
            "reaction_total_ton",
            "status",
            "inside_cap"
        ]
    ]

    display_df = display_df.rename(columns={
        "Pile": "เสาเข็ม",
        "x_cm": "x (cm)",
        "y_cm": "y (cm)",
        "x_rel_cm": "x จาก CG (cm)",
        "y_rel_cm": "y จาก CG (cm)",
        "reaction_basic_ton": "P/n (ton)",
        "reaction_from_Mx_ton": "ผลจาก Mx (ton)",
        "reaction_from_My_ton": "ผลจาก My (ton)",
        "reaction_total_ton": "R รวม (ton)",
        "status": "สถานะ",
        "inside_cap": "อยู่ในฐานราก"
    })

    st.dataframe(
        display_df.style.format({
            "x (cm)": "{:.2f}",
            "y (cm)": "{:.2f}",
            "x จาก CG (cm)": "{:.2f}",
            "y จาก CG (cm)": "{:.2f}",
            "P/n (ton)": "{:.2f}",
            "ผลจาก Mx (ton)": "{:.2f}",
            "ผลจาก My (ton)": "{:.2f}",
            "R รวม (ton)": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("🧮 สรุปค่าโมเมนต์")

    summary_table = pd.DataFrame({
        "รายการ": [
            "P รวม",
            "จำนวนเสาเข็ม",
            "P/n",
            "ex",
            "ey",
            "Mx = P × ey",
            "My = P × ex",
            "Σx²",
            "Σy²",
            "ผลรวม R"
        ],
        "ค่า": [
            summary["P_total"],
            n_piles,
            summary["P_each"],
            ex_cm,
            ey_cm,
            summary["Mx"],
            summary["My"],
            summary["sum_x2"],
            summary["sum_y2"],
            summary["R_sum"]
        ],
        "หน่วย": [
            "ton",
            "ต้น",
            "ton/pile",
            "cm",
            "cm",
            "ton-cm",
            "ton-cm",
            "cm²",
            "cm²",
            "ton"
        ]
    })

    st.dataframe(
        summary_table.style.format({"ค่า": "{:.2f}"}),
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# ENGINEERING RECOMMENDATIONS
# =========================================================
st.subheader("📝 คำแนะนำทางวิศวกรรม")

if all_safe:
    st.success(
        "เสาเข็มทุกต้นรับแรงไม่เกินค่าปลอดภัย และไม่เกิดแรงดึง สามารถใช้เป็นผลตรวจสอบเบื้องต้นได้"
    )
else:
    recommendations = []

    if (df_result["reaction_total_ton"] > safe_capacity_ton).any():
        recommendations.append(
            "เพิ่มจำนวนเสาเข็ม หรือเพิ่มกำลังรับน้ำหนักปลอดภัยของเสาเข็ม"
        )
        recommendations.append(
            "ปรับตำแหน่งเสาเข็มให้กระจายออกจากจุดศูนย์กลางมากขึ้น เพื่อลดแรงที่เสาเข็มต้นวิกฤต"
        )

    if (df_result["reaction_total_ton"] < 0).any():
        recommendations.append(
            "ลดระยะเยื้องศูนย์ ex หรือ ey เนื่องจากมีเสาเข็มเกิดแรงดึง"
        )
        recommendations.append(
            "พิจารณาเพิ่มขนาดฐานรากหรือเปลี่ยนตำแหน่งกลุ่มเสาเข็ม"
        )

    if not all_inside:
        recommendations.append(
            "ปรับตำแหน่งเสาเข็มให้อยู่ภายในขอบเขตฐานราก"
        )

    for rec in recommendations:
        st.warning(f"• {rec}")

# =========================================================
# FORMULA SECTION
# =========================================================
with st.expander("📘 แสดงสมการที่ใช้ในการคำนวณ", expanded=False):
    st.markdown(
        """
        โปรแกรมนี้ใช้สมมติฐานว่า pile cap มีพฤติกรรมแข็งเกร็ง และเสาเข็มแต่ละต้นมี stiffness ใกล้เคียงกัน

        **แรงพื้นฐานต่อเสาเข็ม**

        \[
        R_0 = \\frac{P}{n}
        \]

        **โมเมนต์จากแรงเยื้องศูนย์**

        \[
        M_x = P e_y
        \]

        \[
        M_y = P e_x
        \]

        **แรงปฏิกิริยาเสาเข็มต้นที่ i**

        \[
        R_i = \\frac{P}{n} + \\frac{M_x y_i}{\\sum y_i^2} + \\frac{M_y x_i}{\\sum x_i^2}
        \]

        โดย \(x_i\) และ \(y_i\) คือพิกัดเสาเข็มที่วัดจากจุดศูนย์กลางกลุ่มเสาเข็ม
        """
    )

# =========================================================
# EXPORT
# =========================================================
st.subheader("📤 Export รายงาน")

excel_file = export_to_excel(df_result, summary, safe_capacity_ton)

st.download_button(
    label="Download Excel Report",
    data=excel_file,
    file_name="pile_reaction_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================================================
# DISCLAIMER
# =========================================================
st.caption(
    "หมายเหตุ: โปรแกรมนี้เหมาะสำหรับการตรวจสอบเบื้องต้นและการเรียนการสอน "
    "ก่อนนำไปใช้ในงานจริงควรให้วิศวกรผู้รับผิดชอบตรวจสอบสมมติฐาน หน่วย และรายละเอียดตามมาตรฐานที่เกี่ยวข้องอีกครั้ง"
)
