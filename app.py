import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Smart Sales Dashboard", layout="wide")

st.title("📊 Smart Dynamic Sales Dashboard")
st.write("Adaptive dashboard based on uploaded data ✅")

# -------------------------------
# Helper: Find matching column
# -------------------------------
def find_column(df, possible_names):
    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None

# -------------------------------
# Load Data
# -------------------------------
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

    st.write("### 🔍 Detected Columns:")
    st.write(df.columns.tolist())

    # Detect columns
    date_col = find_column(df, ['date'])
    product_col = find_column(df, ['product'])
    customer_col = find_column(df, ['customer'])
    qty_col = find_column(df, ['qty', 'quantity'])

    # Convert
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])  # FIX: remove invalid dates
        df['Month'] = df[date_col].dt.strftime('%Y-%m')

    if qty_col:
        df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce')
        df = df.dropna(subset=[qty_col])  # FIX: remove invalid qty

    # -------------------------------
    # FILTERS
    # -------------------------------
    st.sidebar.header("🔍 Filters")

    filtered_df = df.copy()

    if product_col:
        products = df[product_col].dropna().unique()
        selected_products = st.sidebar.multiselect("Product", products, default=products)
        if selected_products:
            filtered_df = filtered_df[filtered_df[product_col].isin(selected_products)]

    if customer_col:
        customers = df[customer_col].dropna().unique()
        selected_customers = st.sidebar.multiselect("Customer", customers, default=customers)
        if selected_customers:
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
    # KPIs (Quantity Based)
    # -------------------------------
    st.markdown("## 📊 Key Metrics")

    col1, col2, col3 = st.columns(3)

    if qty_col:
        col1.metric("Total Quantity (KG)", f"{filtered_df[qty_col].sum():,.0f}")

    if product_col:
        col2.metric("Total Products", filtered_df[product_col].nunique())

    if customer_col:
        col3.metric("Customers", filtered_df[customer_col].nunique())

    st.markdown("---")

    # -------------------------------
    # Charts
    # -------------------------------
    col1, col2 = st.columns(2)

    # Top Products
    if product_col and qty_col and not filtered_df.empty:
        with col1:
            st.subheader("📦 Top Products (by KG)")
            top_products = (
                filtered_df.groupby(product_col)[qty_col]
                .sum()
                .sort_values(ascending=False)
                .head(10)
            )

            fig = px.bar(
                x=top_products.values,
                y=top_products.index,
                orientation='h'
            )
            st.plotly_chart(fig, use_container_width=True)

    # Top Customers
    if customer_col and qty_col and not filtered_df.empty:
        with col2:
            st.subheader("👥 Top Customers (by KG)")
            top_customers = (
                filtered_df.groupby(customer_col)[qty_col]
                .sum()
                .sort_values(ascending=False)
                .head(10)
            )

            fig2 = px.bar(
                x=top_customers.values,
                y=top_customers.index,
                orientation='h'
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Monthly Trend
    if date_col and qty_col and not filtered_df.empty:
        st.subheader("📈 Monthly Quantity Trend")

        monthly = filtered_df.groupby('Month')[qty_col].sum().reset_index()

        fig3 = px.line(monthly, x='Month', y=qty_col, markers=True)
        st.plotly_chart(fig3, use_container_width=True)

    # -------------------------------
    # SMART INSIGHTS
    # -------------------------------
    if not filtered_df.empty:
        st.markdown("---")
        st.subheader("🧠 Smart Insights")

        col1, col2 = st.columns(2)

        if product_col and qty_col:
            top_product = filtered_df.groupby(product_col)[qty_col].sum().idxmax()
            with col1:
                st.success(f"🥇 Top Product: {top_product}")

        if customer_col and qty_col:
            top_customer = filtered_df.groupby(customer_col)[qty_col].sum().idxmax()
            with col2:
                st.success(f"👑 Top Customer: {top_customer}")

        if date_col and qty_col:
            best_month = filtered_df.groupby('Month')[qty_col].sum().idxmax()
            st.info(f"📅 Best Month: {best_month}")

    # -------------------------------
    # Download
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
