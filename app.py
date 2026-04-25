import os
os.environ["STREAMLIT_DATAFRAME_SERIALIZATION"] = "legacy"

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AI Sales Dashboard", layout="wide")

st.title("📊 AI-Powered Sales Analytics Dashboard")
st.write("Smart dashboard with customer behavior insights 🚀")

# -------------------------------
# Helper
# -------------------------------
def find_column(df, possible_names):
    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None

@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# -------------------------------
# Upload
# -------------------------------
uploaded_file = st.file_uploader("Upload your file", type=['csv', 'xlsx'])

# -------------------------------
# MAIN APP
# -------------------------------
if uploaded_file:
    df = load_data(uploaded_file)

    st.success("File uploaded successfully ✅")
    st.text(f"Columns: {list(df.columns)}")

    # Detect columns
    date_col = find_column(df, ['date'])
    product_col = find_column(df, ['product'])
    customer_col = find_column(df, ['customer'])
    qty_col = find_column(df, ['qty', 'quantity'])

    # -------------------------------
    # Data Cleaning
    # -------------------------------
    df[date_col] = pd.to_datetime(df[date_col], format='%b-%y', errors='coerce')
    df = df.dropna(subset=[date_col])

    df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce')
    df = df.dropna(subset=[qty_col])

    df['Month'] = df[date_col].dt.strftime('%Y-%m')
    df['Month_Num'] = df[date_col].dt.to_period('M')

    latest_month = df['Month_Num'].max()

    # -------------------------------
    # FILTERS
    # -------------------------------
    st.sidebar.header("🔍 Filters")

    filtered_df = df.copy()

    if product_col:
        products = df[product_col].dropna().unique()
        selected_products = st.sidebar.multiselect("Product", products, default=products)
        filtered_df = filtered_df[filtered_df[product_col].isin(selected_products)]

    if customer_col:
        customers = df[customer_col].dropna().unique()
        selected_customers = st.sidebar.multiselect("Customer", customers, default=customers)
        filtered_df = filtered_df[filtered_df[customer_col].isin(selected_customers)]

    if date_col and not filtered_df.empty:
        min_date = filtered_df[date_col].min()
        max_date = filtered_df[date_col].max()

        selected_dates = st.sidebar.date_input("Date Range", [min_date, max_date])

        if len(selected_dates) == 2:
            filtered_df = filtered_df[
                (filtered_df[date_col] >= pd.to_datetime(selected_dates[0])) &
                (filtered_df[date_col] <= pd.to_datetime(selected_dates[1]))
            ]

    # -------------------------------
    # KPIs
    # -------------------------------
    st.markdown("## 📊 Key Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Quantity (KG)", f"{filtered_df[qty_col].sum():,.0f}")
    col2.metric("Total Products", filtered_df[product_col].nunique())
    col3.metric("Customers", filtered_df[customer_col].nunique())

    st.markdown("---")

    # -------------------------------
    # Charts
    # -------------------------------
    col1, col2 = st.columns(2)

    if product_col and qty_col and not filtered_df.empty:
        with col1:
            st.subheader("📦 Top Products")
            top_products = filtered_df.groupby(product_col)[qty_col].sum().nlargest(10)

            fig = px.bar(x=top_products.values, y=top_products.index, orientation='h')
            st.plotly_chart(fig, width='stretch')

    if customer_col and qty_col and not filtered_df.empty:
        with col2:
            st.subheader("👥 Top Customers")
            top_customers = filtered_df.groupby(customer_col)[qty_col].sum().nlargest(10)

            fig2 = px.bar(x=top_customers.values, y=top_customers.index, orientation='h')
            st.plotly_chart(fig2, width='stretch')

    if date_col and qty_col and not filtered_df.empty:
        st.subheader("📈 Monthly Trend")

        monthly = filtered_df.groupby('Month')[qty_col].sum().reset_index()
        fig3 = px.line(monthly, x='Month', y=qty_col, markers=True)
        st.plotly_chart(fig3, width='stretch')

    # -------------------------------
    # SMART INSIGHTS
    # -------------------------------
    if not filtered_df.empty:
        st.markdown("---")
        st.subheader("🧠 Smart Insights")

        col1, col2 = st.columns(2)

        top_product = filtered_df.groupby(product_col)[qty_col].sum().idxmax()
        col1.success(f"🥇 Top Product: {top_product}")

        top_customer = filtered_df.groupby(customer_col)[qty_col].sum().idxmax()
        col2.success(f"👑 Top Customer: {top_customer}")

        best_month = filtered_df.groupby('Month')[qty_col].sum().idxmax()
        st.info(f"📅 Best Month: {best_month}")

    # -------------------------------
    # 🧠 CUSTOMER BEHAVIOR (NEW)
    # -------------------------------
    st.markdown("---")
    st.subheader("🧠 Customer Behavior Analysis")

    customer_activity = df.groupby(customer_col)['Month_Num'].apply(list).reset_index()

    analysis = []

    for _, row in customer_activity.iterrows():
        months = sorted(row['Month_Num'])

        if len(months) < 2:
            continue

        gaps = [(months[i] - months[i-1]).n for i in range(1, len(months))]
        avg_gap = sum(gaps) / len(gaps)

        last_purchase = months[-1]
        current_gap = (latest_month - last_purchase).n

        if avg_gap <= 1:
            pattern = "Monthly Buyer"
        elif avg_gap <= 2:
            pattern = "Bi-Monthly Buyer"
        elif avg_gap <= 3:
            pattern = "Quarterly Buyer"
        else:
            pattern = "Rare Buyer"

        status = "Active" if current_gap <= avg_gap else "Inactive"

        analysis.append({
            "Customer": row[customer_col],
            "Pattern": pattern,
            "Avg Gap": round(avg_gap, 1),
            "Current Gap": current_gap,
            "Status": status
        })

    analysis_df = pd.DataFrame(analysis)

    if not analysis_df.empty:
        st.dataframe(analysis_df)

    # -------------------------------
    # 📦 PRODUCT MOVEMENT
    # -------------------------------
    st.markdown("---")
    st.subheader("📦 Product Movement")

    product_sales = df.groupby(product_col)[qty_col].sum().reset_index()
    avg_sales = product_sales[qty_col].mean()

    product_sales['Category'] = product_sales[qty_col].apply(
        lambda x: "Fast Moving" if x >= avg_sales else "Slow Moving"
    )

    st.dataframe(product_sales)

    # -------------------------------
    # 📉 DROP ALERT (FIXED)
    # -------------------------------
    st.markdown("---")
    st.subheader("📉 Drop Alerts")

    pivot = df.groupby([customer_col, 'Month'])[qty_col].sum().unstack().fillna(0)

    if pivot.shape[1] >= 2:
        last = pivot.iloc[:, -1]
        prev = pivot.iloc[:, -2]

        drop = prev - last

        drop_df = drop[drop > 0].sort_values(ascending=False).head(10)

        if not drop_df.empty:
            st.error("Customers with drop in purchase")
            st.dataframe(drop_df)
        else:
            st.success("No drop detected")
    else:
        st.info("Need at least 2 months data")

    # -------------------------------
    # 🔮 SEASONAL DEMAND
    # -------------------------------
    st.markdown("---")
    st.subheader("🔮 Seasonal Demand Insight")

    df['Month_Name'] = df[date_col].dt.strftime('%b')

    season = df.groupby(['Month_Name', product_col])[qty_col].sum().reset_index()
    top_season = season.sort_values(by=qty_col, ascending=False).head(10)

    st.dataframe(top_season)

    # -------------------------------
    # DOWNLOAD
    # -------------------------------
    st.markdown("---")
    st.subheader("⬇️ Download Data")

    st.download_button(
        "Download Filtered Data",
        filtered_df.to_csv(index=False),
        "filtered_data.csv",
        "text/csv"
    )

else:
    st.info("Upload a file to generate dashboard")